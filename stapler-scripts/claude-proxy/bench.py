#!/usr/bin/env python3
"""
bench.py — Benchmarking CLI for stapler-compactor.

Commands:
  dry-run   Run all benchmark payloads through /v1/messages/dry-run, print table
  compare   Run same payloads against two ports, compare side-by-side
  watch     Poll /metrics every 2s and print live compression stats

Benchmark scenarios:
  short         2-turn Q&A — below floor, never compresses (baseline)
  code-review   Multi-turn review with code blocks
  tool-heavy    Multiple tool_result JSON blobs (tool content bypasses compressor)
  log-dump      Large log output in user/assistant messages — high compression
  stack-trace   Chained exception chains pasted into chat — very high compression
  junit-xml     JUnit Surefire XML test report — very high compression
  xml-config    Spring beans + Maven POM — very high compression
  code-explorer Agent reads all files in a project (dynamic, uses real files)
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Benchmark payloads — static synthetic scenarios
# ---------------------------------------------------------------------------

_CODE_BLOCK = """```python
def process_events(events: list[dict]) -> dict[str, int]:
    \"\"\"Aggregate event counts by type with deduplication.\"\"\"
    seen = set()
    counts: dict[str, int] = {}
    for event in events:
        key = (event.get('type'), event.get('id'))
        if key in seen:
            continue
        seen.add(key)
        etype = event.get('type', 'unknown')
        counts[etype] = counts.get(etype, 0) + 1
    return counts
```"""

_REVIEW_FEEDBACK = """Looking at this function, a few things stand out:

1. **Type safety**: The `events` parameter accepts `list[dict]` but `event.get('id')` could return `None`, making the dedup key `(type, None)` which might not be what you want. Consider requiring an `id` field.

2. **Performance**: Using a `(type, id)` tuple as the set key is fine for small lists, but for large event streams you might want to benchmark against a simpler `id`-only dedup if IDs are globally unique.

3. **Edge cases**: What happens when `events` is empty? Currently returns `{}` which is correct. What if `event` is missing the `type` key entirely? Falls back to `'unknown'` — intentional?

4. **Naming**: `process_events` is generic. `count_events_by_type` or `aggregate_event_counts` communicates the intent more clearly.

Overall the logic is sound. I'd make the ID handling explicit and rename the function."""

_TOOL_RESULT_JSON = json.dumps({
    "status": "success",
    "data": {
        "items": [
            {"id": f"item-{i}", "name": f"Widget {i}", "price": round(9.99 + i * 0.5, 2),
             "tags": ["electronics", "sale"], "in_stock": i % 2 == 0}
            for i in range(20)
        ],
        "pagination": {"page": 1, "per_page": 20, "total": 143, "total_pages": 8},
        "filters_applied": {"category": "electronics", "min_price": 9.99, "max_price": 20.0},
    }
})

_LOG_OUTPUT = "\n".join([
    f"2026-04-07T{10+i//60:02d}:{i%60:02d}:00Z INFO  [request-{1000+i}] Processing webhook event type=order.created customer_id=cust_{i % 500} order_id=ord_{i}"
    for i in range(60)
] + [
    "2026-04-07T10:58:00Z WARN  [worker-3] High memory usage: 82% — GC pressure detected",
    "2026-04-07T10:58:01Z ERROR [db-pool] Connection timeout after 5000ms — retrying (attempt 1/3)",
    "2026-04-07T10:58:03Z ERROR [db-pool] Connection timeout after 5000ms — retrying (attempt 2/3)",
    "2026-04-07T10:58:05Z INFO  [db-pool] Connection recovered after 5.2s",
    "2026-04-07T10:59:00Z INFO  [scheduler] Running hourly reconciliation job",
    "2026-04-07T10:59:12Z INFO  [reconciler] Processed 1,847 records, 3 discrepancies found",
])

def _gen_stack_trace() -> str:
    """Realistic Python exception chain from a FastAPI payment service, ~100 frames."""
    _frames = [
        ("api/v1/routes/orders.py", 143, "create_order", "result = await order_service.create(current_user, request)"),
        ("api/v1/routes/orders.py", 89, "create_order", "await rate_limiter.check(current_user.id)"),
        ("core/middleware/auth.py", 67, "__call__", "response = await self.app(scope, receive, send)"),
        ("services/order_service.py", 287, "create", "inventory_check = await inventory.reserve(items)"),
        ("services/order_service.py", 234, "create", "price_total = await pricing.calculate(items, user)"),
        ("services/inventory_service.py", 156, "reserve", "rows = await db.execute(stmt)"),
        ("services/inventory_service.py", 120, "reserve", "async with db.begin() as txn:"),
        ("core/db/session.py", 88, "begin", "conn = await self.pool.acquire()"),
        ("core/db/pool.py", 45, "acquire", "return await asyncio.wait_for(self._get_conn(), timeout=5.0)"),
        ("core/db/pool.py", 102, "_get_conn", "sock = await asyncio.open_connection(self.host, self.port)"),
    ]
    _frames2 = [
        ("services/order_service.py", 291, "create", "raise ServiceUnavailableError('Inventory service unavailable') from exc"),
        ("services/order_service.py", 245, "_validate", "await self._check_fraud_signals(user, items)"),
        ("services/fraud/detector.py", 78, "_check_fraud_signals", "score = await self.model.predict(features)"),
        ("services/fraud/model.py", 34, "predict", "return self._clf.decision_function(X)"),
        ("api/v1/routes/orders.py", 148, "create_order", "raise HTTPException(status_code=503, detail=str(exc)) from exc"),
    ]
    _frames3 = [
        ("api/middleware/error_handler.py", 55, "__call__", "response = await call_next(request)"),
        ("api/middleware/error_handler.py", 62, "__call__", "await self.reporter.capture(request, exc)"),
        ("core/reporting/sentry_reporter.py", 29, "capture", "sentry_sdk.capture_exception(exc)"),
        ("core/reporting/sentry_reporter.py", 41, "capture", "extra = await self._enrich_context(request)"),
        ("core/reporting/sentry_reporter.py", 58, "_enrich_context", "user = await get_current_user(request)"),
        ("core/auth/dependencies.py", 112, "get_current_user", "payload = jwt.decode(token, settings.SECRET_KEY)"),
    ]

    def _tb(frames, exc_type, exc_msg):
        lines = ["Traceback (most recent call last):"]
        for path, lineno, func, code in frames:
            lines.append(f'  File "/app/{path}", line {lineno}, in {func}')
            lines.append(f"    {code}")
        lines.append(f"{exc_type}: {exc_msg}")
        return "\n".join(lines)

    return "\n\n".join([
        _tb(_frames,
            "sqlalchemy.exc.OperationalError",
            "(psycopg2.OperationalError) could not connect to server: Connection refused\n"
            "(Background on this error at: https://sqlalche.me/e/14/e3q8)"),
        "The above exception was the direct cause of the following exception:",
        _tb(_frames2,
            "app.exceptions.ServiceUnavailableError",
            "Inventory service unavailable — db pool exhausted after 5000ms"),
        "The above exception was the direct cause of the following exception:",
        _tb(_frames3,
            "app.exceptions.ReportingError",
            "Failed to capture exception to Sentry: JWT signature verification failed"),
        "During handling of the above exception, another exception occurred:",
        _tb([
            ("core/middleware/logging.py", 31, "__call__", "await self.logger.log_request(request, response, duration)"),
            ("core/middleware/logging.py", 44, "log_request", "payload = await request.body()"),
            ("starlette/requests.py", 267, "body", "body = b''.join([chunk async for chunk in self.stream()])"),
        ],
            "starlette.requests.ClientDisconnect",
            "client disconnected"),
    ])


def _gen_junit_xml() -> str:
    """JUnit 5 Surefire XML report with 85 tests, 5 failures, 2 errors."""
    import xml.etree.ElementTree as ET
    suite = ET.Element("testsuite", {
        "name": "com.example.platform.PaymentServiceIntegrationTest",
        "tests": "85", "failures": "5", "errors": "2", "skipped": "3",
        "time": "47.821", "timestamp": "2026-04-07T10:30:00",
        "hostname": "ci-runner-04",
    })
    passing = [
        ("testProcessPayment_success_creditCard", 0.423),
        ("testProcessPayment_success_debitCard", 0.311),
        ("testProcessPayment_success_applePay", 0.287),
        ("testRefund_fullRefund_withinWindow", 0.654),
        ("testRefund_partialRefund", 0.512),
        ("testRefund_failsAfter30Days", 0.198),
        ("testWebhook_paymentSucceeded", 0.087),
        ("testWebhook_paymentFailed", 0.091),
        ("testWebhook_disputeCreated", 0.105),
        ("testWebhook_refundCreated", 0.093),
        ("testIdempotency_duplicateRequestReturnsOriginal", 1.234),
        ("testIdempotency_expiredKeyStartsNewPayment", 0.876),
        ("testCurrency_usdDefault", 0.112),
        ("testCurrency_eurConversion", 0.234),
        ("testCurrency_gbpConversion", 0.221),
        ("testCurrency_jpyNoDecimal", 0.189),
        ("testCurrency_invalidCodeRejected", 0.067),
        ("testRateLimit_under100rps", 0.445),
        ("testRateLimit_at100rps", 0.523),
        ("testAuth_validBearerToken", 0.178),
        ("testAuth_expiredToken", 0.145),
        ("testAuth_invalidSignature", 0.134),
        ("testAuth_missingToken", 0.089),
        ("testMetadata_storedOnCharge", 0.312),
        ("testMetadata_retrievedOnFetch", 0.298),
        ("testMetadata_maxKeysEnforced", 0.201),
        ("testCapture_authorizeOnly", 0.567),
        ("testCapture_captureAuthorized", 0.489),
        ("testCapture_cancelAuthorized", 0.334),
        ("test3DS_requiresAuthentication", 0.723),
        ("test3DS_authenticatedSuccess", 0.654),
        ("test3DS_failedAuthentication", 0.345),
        ("testSCA_exemptionApplied", 0.412),
        ("testSCA_challengeRequired", 0.587),
        ("testFraud_lowRiskApproved", 0.223),
        ("testFraud_highRiskDeclined", 0.198),
        ("testFraud_reviewQueue", 0.312),
        ("testDispute_created", 0.445),
        ("testDispute_evidence_submitted", 0.678),
        ("testDispute_won", 0.534),
        ("testDispute_lost", 0.489),
        ("testPayout_scheduled", 0.312),
        ("testPayout_instantAvailable", 0.423),
        ("testPayout_insufficientFunds", 0.189),
        ("testCustomer_create", 0.234),
        ("testCustomer_updateEmail", 0.198),
        ("testCustomer_addPaymentMethod", 0.312),
        ("testCustomer_deletePaymentMethod", 0.278),
        ("testCustomer_setDefaultPaymentMethod", 0.234),
        ("testBalanceTransaction_list", 0.567),
        ("testBalanceTransaction_retrieve", 0.312),
        ("testEvent_list", 0.423),
        ("testEvent_retrieve", 0.198),
        ("testEvent_listByType", 0.312),
        ("testWebhookEndpoint_create", 0.445),
        ("testWebhookEndpoint_update", 0.389),
        ("testWebhookEndpoint_delete", 0.223),
        ("testWebhookEndpoint_listEvents", 0.512),
        ("testProduct_create", 0.345),
        ("testProduct_update", 0.312),
        ("testProduct_archive", 0.198),
        ("testPrice_createFixed", 0.289),
        ("testPrice_createRecurring", 0.334),
        ("testPrice_deactivate", 0.178),
        ("testSubscription_create", 0.789),
        ("testSubscription_pause", 0.567),
        ("testSubscription_cancel", 0.489),
        ("testSubscription_resume", 0.534),
        ("testInvoice_draft", 0.445),
        ("testInvoice_finalize", 0.523),
        ("testInvoice_pay", 0.678),
        ("testInvoice_void", 0.398),
        ("testPaymentIntent_create", 0.512),
        ("testPaymentIntent_confirm", 0.623),
        ("testPaymentIntent_cancel", 0.334),
        ("testSetupIntent_create", 0.445),
        ("testSetupIntent_confirm", 0.567),
    ]
    failures = [
        ("testRateLimit_exceed100rps",
         "expected status 429 but was 200",
         "org.opentest4j.AssertionFailedError: expected status 429 but was 200\n"
         "\tat com.example.platform.PaymentServiceIntegrationTest.testRateLimit_exceed100rps(PaymentServiceIntegrationTest.java:412)\n"
         "\tat java.base/jdk.internal.reflect.NativeMethodAccessorImpl.invoke0(Native Method)\n"
         "\tat java.base/jdk.internal.reflect.NativeMethodAccessorImpl.invoke(NativeMethodAccessorImpl.java:77)"),
        ("testFraud_cardTestingDetected",
         "expected FraudException but no exception was thrown",
         "org.opentest4j.AssertionFailedError: Expected com.example.exceptions.FraudException to be thrown, but nothing was thrown.\n"
         "\tat com.example.platform.PaymentServiceIntegrationTest.testFraud_cardTestingDetected(PaymentServiceIntegrationTest.java:567)"),
        ("testDispute_evidenceDeadlineEnforced",
         "Expected deadline validation to reject evidence after 7 days",
         "org.opentest4j.AssertionFailedError: expected <true> but was <false>\n"
         "\tat com.example.platform.PaymentServiceIntegrationTest.testDispute_evidenceDeadlineEnforced(PaymentServiceIntegrationTest.java:634)"),
        ("testWebhook_signatureValidation",
         "HMAC-SHA256 signature mismatch on replay test",
         "org.opentest4j.AssertionFailedError: ==> expected: <invalid_signature> but was: <valid_signature>\n"
         "\tat com.example.platform.PaymentServiceIntegrationTest.testWebhook_signatureValidation(PaymentServiceIntegrationTest.java:298)"),
        ("testSubscription_trialPeriodBilling",
         "Trial end date off by one day",
         "org.opentest4j.AssertionFailedError: ==> expected: <2026-05-07> but was: <2026-05-08>\n"
         "\tat com.example.platform.PaymentServiceIntegrationTest.testSubscription_trialPeriodBilling(PaymentServiceIntegrationTest.java:723)"),
    ]
    errors = [
        ("testPaymentIntent_3dsRedirect",
         "org.springframework.web.client.ResourceAccessException",
         "org.springframework.web.client.ResourceAccessException: I/O error on POST request for "
         "\"https://hooks.stripe.com/redirect/authenticate/...\": Connection refused; "
         "nested exception is java.net.ConnectException: Connection refused\n"
         "\tat org.springframework.web.client.RestTemplate.doExecute(RestTemplate.java:776)"),
        ("testConnectivity_stripeWebhook",
         "java.net.SocketTimeoutException",
         "java.net.SocketTimeoutException: Read timed out\n"
         "\tat java.base/java.net.SocketInputStream.socketRead0(Native Method)\n"
         "\tat java.base/sun.nio.cs.StreamDecoder.readBytes(StreamDecoder.java:284)"),
    ]
    skipped = ["testPayout_internationalWire", "testSCA_openBankingFlow", "testFraud_velocityCheck_disabled"]

    classname = "com.example.platform.PaymentServiceIntegrationTest"
    for name, t in passing:
        ET.SubElement(suite, "testcase", {"name": name, "classname": classname, "time": str(t)})
    for name, msg, detail in failures:
        tc = ET.SubElement(suite, "testcase", {"name": name, "classname": classname, "time": "0.001"})
        ET.SubElement(tc, "failure", {"message": msg, "type": "org.opentest4j.AssertionFailedError"}).text = detail
    for name, etype, detail in errors:
        tc = ET.SubElement(suite, "testcase", {"name": name, "classname": classname, "time": "0.001"})
        ET.SubElement(tc, "error", {"message": etype, "type": etype}).text = detail
    for name in skipped:
        tc = ET.SubElement(suite, "testcase", {"name": name, "classname": classname, "time": "0.000"})
        ET.SubElement(tc, "skipped")

    ET.indent(suite, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(suite, encoding="unicode")


def _gen_xml_config() -> str:
    """Realistic Spring beans XML + Maven POM combined."""
    spring = '''<?xml version="1.0" encoding="UTF-8"?>
<beans xmlns="http://www.springframework.org/schema/beans"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xmlns:context="http://www.springframework.org/schema/context"
       xmlns:tx="http://www.springframework.org/schema/tx"
       xmlns:security="http://www.springframework.org/schema/security"
       xsi:schemaLocation="
         http://www.springframework.org/schema/beans
         https://www.springframework.org/schema/beans/spring-beans.xsd
         http://www.springframework.org/schema/context
         https://www.springframework.org/schema/context/spring-context.xsd
         http://www.springframework.org/schema/tx
         https://www.springframework.org/schema/tx/spring-tx.xsd">

    <context:property-placeholder location="classpath:application.properties"/>
    <context:component-scan base-package="com.example.platform"/>
    <tx:annotation-driven transaction-manager="transactionManager"/>

    <!-- ================================================================ -->
    <!-- DataSource                                                         -->
    <!-- ================================================================ -->
    <bean id="dataSource" class="com.zaxxer.hikari.HikariDataSource" destroy-method="close">
        <property name="driverClassName" value="org.postgresql.Driver"/>
        <property name="jdbcUrl" value="${db.url:jdbc:postgresql://localhost:5432/platform}"/>
        <property name="username" value="${db.username:platform}"/>
        <property name="password" value="${db.password}"/>
        <property name="minimumIdle" value="${db.pool.minIdle:5}"/>
        <property name="maximumPoolSize" value="${db.pool.maxSize:20}"/>
        <property name="connectionTimeout" value="30000"/>
        <property name="idleTimeout" value="600000"/>
        <property name="maxLifetime" value="1800000"/>
        <property name="leakDetectionThreshold" value="60000"/>
    </bean>

    <!-- ================================================================ -->
    <!-- JPA / EntityManagerFactory                                        -->
    <!-- ================================================================ -->
    <bean id="entityManagerFactory"
          class="org.springframework.orm.jpa.LocalContainerEntityManagerFactoryBean">
        <property name="dataSource" ref="dataSource"/>
        <property name="packagesToScan" value="com.example.platform.domain"/>
        <property name="jpaVendorAdapter">
            <bean class="org.springframework.orm.jpa.vendor.HibernateJpaVendorAdapter">
                <property name="showSql" value="${jpa.showSql:false}"/>
                <property name="generateDdl" value="false"/>
                <property name="databasePlatform" value="org.hibernate.dialect.PostgreSQLDialect"/>
            </bean>
        </property>
        <property name="jpaProperties">
            <props>
                <prop key="hibernate.hbm2ddl.auto">validate</prop>
                <prop key="hibernate.format_sql">true</prop>
                <prop key="hibernate.use_sql_comments">true</prop>
                <prop key="hibernate.jdbc.batch_size">50</prop>
                <prop key="hibernate.order_inserts">true</prop>
                <prop key="hibernate.order_updates">true</prop>
                <prop key="hibernate.cache.use_second_level_cache">true</prop>
                <prop key="hibernate.cache.region.factory_class">org.hibernate.cache.jcache.JCacheRegionFactory</prop>
            </props>
        </property>
    </bean>

    <bean id="transactionManager" class="org.springframework.orm.jpa.JpaTransactionManager">
        <property name="entityManagerFactory" ref="entityManagerFactory"/>
    </bean>

    <!-- ================================================================ -->
    <!-- Redis / Cache                                                      -->
    <!-- ================================================================ -->
    <bean id="jedisConnectionFactory"
          class="org.springframework.data.redis.connection.jedis.JedisConnectionFactory">
        <property name="hostName" value="${redis.host:localhost}"/>
        <property name="port" value="${redis.port:6379}"/>
        <property name="password" value="${redis.password:}"/>
        <property name="database" value="0"/>
        <property name="usePool" value="true"/>
    </bean>

    <bean id="redisTemplate" class="org.springframework.data.redis.core.RedisTemplate">
        <property name="connectionFactory" ref="jedisConnectionFactory"/>
        <property name="keySerializer">
            <bean class="org.springframework.data.redis.serializer.StringRedisSerializer"/>
        </property>
        <property name="valueSerializer">
            <bean class="org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer"/>
        </property>
    </bean>

    <bean id="cacheManager" class="org.springframework.data.redis.cache.RedisCacheManager">
        <constructor-arg ref="redisTemplate"/>
        <property name="defaultExpiration" value="3600"/>
        <property name="cacheNames">
            <list>
                <value>payments</value>
                <value>customers</value>
                <value>products</value>
                <value>prices</value>
                <value>subscriptions</value>
                <value>exchange_rates</value>
            </list>
        </property>
    </bean>

    <!-- ================================================================ -->
    <!-- Messaging / Kafka                                                  -->
    <!-- ================================================================ -->
    <bean id="producerFactory"
          class="org.springframework.kafka.core.DefaultKafkaProducerFactory">
        <constructor-arg>
            <map>
                <entry key="bootstrap.servers" value="${kafka.bootstrap:localhost:9092}"/>
                <entry key="key.serializer" value="org.apache.kafka.common.serialization.StringSerializer"/>
                <entry key="value.serializer" value="org.springframework.kafka.support.serializer.JsonSerializer"/>
                <entry key="acks" value="all"/>
                <entry key="retries" value="3"/>
                <entry key="enable.idempotence" value="true"/>
                <entry key="max.in.flight.requests.per.connection" value="5"/>
            </map>
        </constructor-arg>
    </bean>

    <bean id="kafkaTemplate" class="org.springframework.kafka.core.KafkaTemplate">
        <constructor-arg ref="producerFactory"/>
        <property name="defaultTopic" value="payment-events"/>
    </bean>

    <bean id="consumerFactory"
          class="org.springframework.kafka.core.DefaultKafkaConsumerFactory">
        <constructor-arg>
            <map>
                <entry key="bootstrap.servers" value="${kafka.bootstrap:localhost:9092}"/>
                <entry key="group.id" value="platform-payment-consumer"/>
                <entry key="key.deserializer" value="org.apache.kafka.common.serialization.StringDeserializer"/>
                <entry key="value.deserializer" value="org.springframework.kafka.support.serializer.JsonDeserializer"/>
                <entry key="auto.offset.reset" value="earliest"/>
                <entry key="enable.auto.commit" value="false"/>
                <entry key="isolation.level" value="read_committed"/>
            </map>
        </constructor-arg>
    </bean>

    <!-- ================================================================ -->
    <!-- Stripe / External Services                                        -->
    <!-- ================================================================ -->
    <bean id="stripeConfig" class="com.example.platform.config.StripeConfiguration">
        <property name="apiKey" value="${stripe.api.key}"/>
        <property name="webhookSecret" value="${stripe.webhook.secret}"/>
        <property name="apiVersion" value="2024-06-20"/>
        <property name="maxNetworkRetries" value="3"/>
        <property name="connectTimeout" value="30"/>
        <property name="readTimeout" value="80"/>
    </bean>

    <bean id="paymentGateway" class="com.example.platform.gateway.StripePaymentGateway">
        <constructor-arg ref="stripeConfig"/>
        <constructor-arg ref="redisTemplate"/>
        <property name="idempotencyKeyTtlSeconds" value="86400"/>
    </bean>

    <bean id="fraudDetector" class="com.example.platform.fraud.StripeRadarFraudDetector">
        <constructor-arg ref="stripeConfig"/>
        <property name="riskThreshold" value="${fraud.risk.threshold:75}"/>
        <property name="reviewThreshold" value="${fraud.review.threshold:50}"/>
    </bean>
</beans>'''

    pom = '''<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
           https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.4</version>
        <relativePath/>
    </parent>
    <groupId>com.example</groupId>
    <artifactId>platform-payment-service</artifactId>
    <version>2.14.0-SNAPSHOT</version>
    <name>Platform Payment Service</name>
    <properties>
        <java.version>21</java.version>
        <stripe.version>25.3.0</stripe.version>
        <testcontainers.version>1.19.7</testcontainers.version>
        <mapstruct.version>1.5.5.Final</mapstruct.version>
    </properties>
    <dependencies>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-data-jpa</artifactId></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-data-redis</artifactId></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-security</artifactId></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-actuator</artifactId></dependency>
        <dependency><groupId>org.springframework.kafka</groupId><artifactId>spring-kafka</artifactId></dependency>
        <dependency><groupId>com.stripe</groupId><artifactId>stripe-java</artifactId><version>${stripe.version}</version></dependency>
        <dependency><groupId>org.postgresql</groupId><artifactId>postgresql</artifactId><scope>runtime</scope></dependency>
        <dependency><groupId>com.zaxxer</groupId><artifactId>HikariCP</artifactId></dependency>
        <dependency><groupId>org.flywaydb</groupId><artifactId>flyway-core</artifactId></dependency>
        <dependency><groupId>org.mapstruct</groupId><artifactId>mapstruct</artifactId><version>${mapstruct.version}</version></dependency>
        <dependency><groupId>org.projectlombok</groupId><artifactId>lombok</artifactId><optional>true</optional></dependency>
        <dependency><groupId>io.micrometer</groupId><artifactId>micrometer-registry-datadog</artifactId></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-test</artifactId><scope>test</scope></dependency>
        <dependency><groupId>org.testcontainers</groupId><artifactId>postgresql</artifactId><version>${testcontainers.version}</version><scope>test</scope></dependency>
        <dependency><groupId>org.testcontainers</groupId><artifactId>kafka</artifactId><version>${testcontainers.version}</version><scope>test</scope></dependency>
    </dependencies>
</project>'''

    return spring + "\n\n<!-- Maven POM -->\n" + pom


def _build_code_explorer_payload(directory: str) -> list[dict]:
    """
    Build a 'read all code' scenario from real .py files in a directory.
    Simulates an agent doing codebase analysis: tool_use calls → tool_result blocks.
    Tool_result content is NOT compressed by FusionEngine (by design), so this
    shows the mixed-mode behaviour of real Claude Code sessions.
    """
    code_exts = {".py", ".ts", ".js", ".go", ".java", ".kt", ".rs"}
    max_files = 12
    max_file_bytes = 8_000  # truncate very large files

    path = Path(directory).expanduser().resolve()
    files = sorted(
        f for f in path.rglob("*")
        if f.is_file() and f.suffix in code_exts
        and not any(part.startswith((".", "__pycache__", "node_modules", ".venv", "venv", "build", "dist"))
                    for part in f.parts)
    )[:max_files]

    if not files:
        return [{"role": "user", "content": f"No code files found in {directory}"}]

    # Build assistant message with tool_use calls for each file
    tool_uses = [
        {"type": "text", "text": f"I'll read all {len(files)} files in {path.name}/ to understand the codebase."},
    ]
    tool_results = []
    for i, f in enumerate(files):
        tu_id = f"tu_{i:03d}"
        rel = str(f.relative_to(path))
        tool_uses.append({
            "type": "tool_use", "id": tu_id, "name": "read_file",
            "input": {"path": rel},
        })
        content = f.read_bytes()[:max_file_bytes].decode("utf-8", errors="replace")
        tool_results.append({
            "type": "tool_result", "tool_use_id": tu_id,
            "content": f"```{f.suffix[1:]}\n{content}\n```",
        })

    # Build a realistic analysis response (this text part DOES compress)
    file_list = "\n".join(f"  - {f.relative_to(path)}" for f in files)
    analysis = (
        f"I've read all {len(files)} files. Here's my analysis:\n\n"
        "**Architecture Overview**\n"
        f"The `{path.name}/` codebase is a Python service with the following structure:\n"
        f"{file_list}\n\n"
        "**Entry Point**\n"
        "`main.py` is the FastAPI application entry point. It registers routes, configures middleware, "
        "initializes the compressor via `lifespan()`, and starts the uvicorn server.\n\n"
        "**Core Components**\n"
        "- `config.py` — Environment variable parsing with typed defaults using Python's `os.environ`\n"
        "- `auth.py` — Bearer token extraction and validation; supports both OAuth (sk-ant-oat-*) and API key formats\n"
        "- `fallback.py` — FallbackHandler orchestrates provider failover; records metrics on each attempt\n"
        "- `compactor.py` — FusionEngine middleware; async wrapper around synchronous compression; "
        "OpenFeature flags control per-stage behaviour; double-compression guard via rewind markers\n"
        "- `metrics.py` — MetricsCollector with diskcache persistence and in-memory deques for recent items\n\n"
        "**Provider Layer** (`providers/`)\n"
        "Both `AnthropicProvider` and `BedrockProvider` implement the same `Provider` interface. "
        "BedrockProvider handles model name translation (e.g., `claude-3-sonnet-20240229` → "
        "`anthropic.claude-3-sonnet-20240229-v1:0`) and AWS SSO credential refresh.\n\n"
        "**Compression Pipeline**\n"
        "Requests flow: parse body → compress_messages() → forward to fallback → return response. "
        "FusionEngine runs in a thread pool via asyncio.to_thread() to avoid blocking the event loop. "
        "Rewind markers are embedded when lossy compression fires; rewind_retrieve tool is injected "
        "so Claude can recover compressed content on demand.\n\n"
        "**Key Design Decisions**\n"
        "1. The proxy is stateless — no session IDs, no persistent agent state\n"
        "2. Compression is transparent — Claude Code doesn't know it's happening\n"
        "3. Fail-safe — any compression error falls back to uncompressed forwarding\n"
        "4. The floor (4096 bytes) prevents overhead on small requests\n\n"
        "**How to Add a New Provider**\n"
        "1. Create `providers/myprovider.py` implementing `Provider.send_message()` and `stream_message()`\n"
        "2. Add to the fallback chain in `main.py`: `FallbackHandler([anthropic, my_provider, bedrock])`\n"
        "3. Handle model name translation if the provider uses different naming\n"
        "4. Add credentials to `config.py` and the LaunchAgent plist\n"
    )

    return [
        {"role": "user", "content": f"Please analyze the {path.name}/ codebase and explain what it does, "
                                     "how the components fit together, and how I'd add a new provider."},
        {"role": "assistant", "content": tool_uses},
        {"role": "user", "content": tool_results},
        {"role": "assistant", "content": analysis},
        {"role": "user", "content": "Great summary. Which file has the most complex logic and why? "
                                     "And what would you change about the current architecture if you "
                                     "were starting from scratch?"},
    ]


# Pre-compute static payloads at module load
_STACK_TRACE_TEXT = _gen_stack_trace()
_JUNIT_XML_TEXT = _gen_junit_xml()
_XML_CONFIG_TEXT = _gen_xml_config()

PAYLOADS: dict[str, list[dict]] = {
    "short": [
        {"role": "user", "content": "What's the capital of France?"},
        {"role": "assistant", "content": "Paris."},
        {"role": "user", "content": "And Germany?"},
    ],
    "code-review": [
        {"role": "user", "content": f"Please review this Python function:\n\n{_CODE_BLOCK}"},
        {"role": "assistant", "content": _REVIEW_FEEDBACK},
        {"role": "user", "content": "Good points. Should I add a `strict_id` parameter to make the dedup behaviour explicit?"},
    ],
    "tool-heavy": [
        {"role": "user", "content": "Search for electronics under $20 and show me the results"},
        {"role": "assistant", "content": [
            {"type": "text", "text": "I'll search the product catalog for you."},
            {"type": "tool_use", "id": "tu_001", "name": "search_products",
             "input": {"category": "electronics", "max_price": 20.0}},
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "tu_001", "content": _TOOL_RESULT_JSON},
        ]},
        {"role": "assistant", "content": [
            {"type": "text", "text": "I found 143 electronics items under $20. Here are the first 20:"},
            {"type": "tool_use", "id": "tu_002", "name": "search_products",
             "input": {"category": "electronics", "max_price": 20.0, "page": 2}},
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "tu_002", "content": _TOOL_RESULT_JSON},
        ]},
        {"role": "assistant", "content": "Page 2 retrieved. Which items interest you?"},
        {"role": "user", "content": "Summarise the price distribution across all pages."},
    ],
    "log-dump": [
        {"role": "user", "content": "Analyse these application logs and summarise any issues:\n\n```\n" + _LOG_OUTPUT + "\n```"},
        {"role": "assistant", "content": (
            "From the logs I can see three issues:\n\n"
            "**1. Database connection timeouts (10:58:01–10:58:05)**\n"
            "Two consecutive 5-second timeouts on the db-pool, recovered after 5.2s. "
            "This correlates with the high memory warning at 10:58:00 — GC pressure may have "
            "stalled connection management threads. Monitor for recurrence.\n\n"
            "**2. Memory pressure (10:58:00)**\n"
            "Worker-3 at 82% heap — near the threshold for GC pauses. If this is sustained, "
            "consider tuning the JVM heap or investigating webhook processing memory allocation.\n\n"
            "**3. Reconciliation discrepancies (10:59:12)**\n"
            "3 discrepancies in 1,847 records (0.16%). Below typical alarm threshold but worth "
            "investigating the specific records — are they the same customers repeatedly?\n\n"
            "No service outages. The spike window (10:58–10:59) lasted ~65 seconds and self-resolved."
        )},
        {"role": "user", "content": "Are the DB timeouts likely caused by the GC pressure?"},
    ],
    "stack-trace": [
        {"role": "user", "content": (
            "I'm getting this error in production. Can you help me diagnose it?\n\n"
            "```\n" + _STACK_TRACE_TEXT + "\n```"
        )},
        {"role": "assistant", "content": (
            "This is a cascading failure chain with four exceptions. Let me trace the root cause:\n\n"
            "**Root cause: PostgreSQL connection refused (SQLAlchemy OperationalError)**\n"
            "The db connection pool tried `asyncio.open_connection()` to your Postgres host but got "
            "`Connection refused`. This means either the DB is down, the host/port in config is wrong, "
            "or the pool exhausted all connections and couldn't open a new socket.\n\n"
            "**Chain reaction:**\n"
            "1. `ServiceUnavailableError` — inventory reservation failed because the DB was unreachable\n"
            "2. `ReportingError` — Sentry capture failed because JWT verification failed during context enrichment\n"
            "3. `ClientDisconnect` — The client disconnected while logging was trying to read the request body\n\n"
            "**What to check:**\n"
            "- Is `asyncio.wait_for(..., timeout=5.0)` in `pool.py:45` realistic? 5s is very short for a cold start.\n"
            "- Is your DB accepting connections? `psql -h $DB_HOST -U $DB_USER` from the app container.\n"
            "- Check `maximumPoolSize` in HikariCP — if it's lower than concurrent requests, you'll see this under load.\n"
            "- The JWT failure in `ReportingError` is a red herring — it's a side effect of the disconnect, not the cause.\n\n"
            "**Fix priority:** DB connectivity first, then consider increasing pool size and the connection timeout."
        )},
        {"role": "user", "content": "How do I reproduce this locally to test the fix?"},
    ],
    "junit-xml": [
        {"role": "user", "content": (
            "Here's our CI test report. We have 5 failures and 2 errors that are blocking the release. "
            "Can you triage them by severity and suggest fixes?\n\n"
            "```xml\n" + _JUNIT_XML_TEXT + "\n```"
        )},
        {"role": "assistant", "content": (
            "Triaging the 7 broken tests by severity:\n\n"
            "**P0 — Release blockers (2)**\n\n"
            "1. `testWebhook_signatureValidation` — HMAC-SHA256 mismatch on replay test. "
            "Security-critical: if signature validation is broken, anyone can forge webhook payloads. "
            "Don't ship until fixed. Check if the webhook secret was rotated without updating the test fixture.\n\n"
            "2. `testFraud_cardTestingDetected` — Expected FraudException not thrown. "
            "Revenue-critical: card testing attacks will go undetected in production. "
            "Check if the fraud threshold config changed or if the detector is silently swallowing exceptions.\n\n"
            "**P1 — Ship with ticket (3)**\n\n"
            "3. `testRateLimit_exceed100rps` — Returns 200 instead of 429. Rate limiting is bypassed "
            "at >100 rps. Add a ticket but likely OK for initial release if you have WAF-level rate limiting.\n\n"
            "4. `testSubscription_trialPeriodBilling` — Off-by-one on trial end date. "
            "Will bill customers one day early. Check timezone handling in the trial period calculator.\n\n"
            "5. `testDispute_evidenceDeadlineEnforced` — Deadline validation returns false when it should be true. "
            "Low blast radius — disputes are rare — but creates a compliance gap.\n\n"
            "**P2 — Infrastructure issues (2 errors)**\n\n"
            "`testPaymentIntent_3dsRedirect` and `testConnectivity_stripeWebhook` are connectivity errors "
            "to `hooks.stripe.com`. These are CI environment issues (Stripe not reachable from runner), "
            "not code bugs. Add `@DisabledIfEnvironmentVariable(named = \"CI\", ...)` or mock the HTTP client.\n\n"
            "**Recommended action:** Fix P0s today, open tickets for P1s, disable P2 tests in CI with a comment."
        )},
        {"role": "user", "content": "For the webhook signature failure — what's the most common root cause?"},
    ],
    "xml-config": [
        {"role": "user", "content": (
            "Please review this Spring configuration and POM for issues, security concerns, "
            "and anything that should be updated before we deploy to production:\n\n"
            "```xml\n" + _XML_CONFIG_TEXT + "\n```"
        )},
        {"role": "assistant", "content": (
            "Review across three categories:\n\n"
            "**Security concerns (fix before prod)**\n\n"
            "1. `${stripe.api.key}` and `${stripe.webhook.secret}` — Good that they're externalized, but verify "
            "they're sourced from a secrets manager (AWS Secrets Manager, Vault) not a plain `.properties` file "
            "checked into git. Same for `${db.password}` and `${redis.password:}`.\n\n"
            "2. Redis password: `${redis.password:}` — the empty default means unauthenticated Redis is silently "
            "accepted. Change to `${redis.password}` (no default) to fail fast if the env var isn't set.\n\n"
            "3. `showSql: ${jpa.showSql:false}` — confirm this defaults to `false` in prod. SQL logging leaks "
            "query structure and can expose PII in application logs.\n\n"
            "**Configuration issues**\n\n"
            "4. `JedisConnectionFactory` is deprecated in Spring Data Redis 3.x — you're on Spring Boot 3.2.4 "
            "(POM). Migrate to `LettuceConnectionFactory` which supports reactive streams and connection pooling "
            "without thread-per-connection overhead.\n\n"
            "5. `RedisCacheManager` constructor taking `RedisTemplate` is also deprecated. "
            "Use `RedisCacheManager.builder(redisConnectionFactory).build()` instead.\n\n"
            "6. `hibernate.hbm2ddl.auto=validate` is correct for production but will break on schema drift. "
            "Ensure Flyway migrations run before the app starts (Spring Boot auto-configures this with the "
            "Flyway dependency already in your POM).\n\n"
            "**POM observations**\n\n"
            "7. `stripe.version=25.3.0` — Stripe Java SDK is at 26.x as of early 2026. Check changelog for "
            "breaking changes, but newer versions have improved idempotency key handling.\n\n"
            "8. `testcontainers.version=1.19.7` — 1.20.x is current. 1.19.x has a known memory leak in "
            "container lifecycle management under JUnit 5 parallel test execution.\n\n"
            "Overall the config is production-grade. Fix the Redis auth default and deprecated connection "
            "factory before deploying."
        )},
        {"role": "user", "content": "How do I migrate from JedisConnectionFactory to Lettuce?"},
    ],
}


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _dry_run_one(port: int, name: str, messages: list[dict]) -> dict:
    """Send one payload to /v1/messages/dry-run and return the result dict."""
    url = f"http://localhost:{port}/v1/messages/dry-run"
    payload = {
        "model": "claude-sonnet-4-6",
        "messages": messages,
        "max_tokens": 1,
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            t0 = time.monotonic()
            resp = client.post(url, json=payload, headers={"Authorization": "Bearer bench"})
            elapsed_ms = (time.monotonic() - t0) * 1000
            resp.raise_for_status()
            data = resp.json()
            data["_elapsed_ms"] = elapsed_ms
            data["_name"] = name
            return data
    except httpx.ConnectError:
        return {"_name": name, "_error": f"Cannot connect to port {port} — is the proxy running?"}
    except Exception as e:
        return {"_name": name, "_error": str(e)}


def _fetch_metrics(port: int) -> dict | None:
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"http://localhost:{port}/metrics")
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Table rendering
# ---------------------------------------------------------------------------

def _fmt(n: int, width: int = 7) -> str:
    return str(n).rjust(width)


# Column inner widths (content only, no padding or border chars)
_COL = {"name": 12, "tokens": 7, "ratio": 8, "ms": 5}
# Inner display width per column = content + 1 space each side
_IW = {k: v + 2 for k, v in _COL.items()}  # name=14, tokens=9, ratio=10, ms=7


def _sep(left="╠", mid="╬", right="╣") -> str:
    segs = [
        "═" * _IW["name"],
        "═" * _IW["tokens"],
        "═" * _IW["tokens"],
        "═" * _IW["tokens"],
        "═" * _IW["ratio"],
        "═" * _IW["ms"],
    ]
    return left + mid.join(segs) + right


def _row(name: str, before: str, after: str, saved: str, ratio: str, ms: str) -> str:
    def _cell(v: str, w: int) -> str:
        return f" {v[:w].ljust(w)} "
    parts = [
        _cell(name, _COL["name"]),
        _cell(before, _COL["tokens"]),
        _cell(after, _COL["tokens"]),
        _cell(saved, _COL["tokens"]),
        _cell(ratio, _COL["ratio"]),
        _cell(ms, _COL["ms"]),
    ]
    return "║" + "║".join(parts) + "║"


def _print_table(results: list[dict], port: int) -> None:
    metrics = _fetch_metrics(port)
    floor = "4096B"

    # Total title width = sum of inner widths + separators between columns (5) + outer borders (2)
    total_inner = sum(_IW[k] for k in ("name", "tokens", "tokens", "tokens", "ratio", "ms")) + 5
    title = f" Benchmark — port {port}  (floor: {floor}) "

    print()
    print("╔" + "═" * total_inner + "╗")
    print("║" + title.center(total_inner) + "║")
    print(_sep("╠", "╦", "╣"))
    print(_row("Payload", "Before", "After", "Saved", "Ratio", "ms"))
    print(_sep())

    total_before = total_after = total_saved = 0

    for r in results:
        name = r.get("_name", "?")
        if "_error" in r:
            err_msg = f"ERROR: {r['_error']}"
            print(_row(name, err_msg[:9], "", "", "", ""))
            continue

        c = r.get("compression", {})
        before = c.get("tokens_before", 0)
        after = c.get("tokens_after", 0)
        saved = c.get("tokens_saved", 0)
        pct = c.get("reduction_pct", 0.0)
        ms = int(r.get("_elapsed_ms", 0))
        skipped = c.get("skipped", False)

        total_before += before
        total_after += after
        total_saved += saved

        ratio_str = "skip" if skipped else f"{pct:.1f}%"
        print(_row(
            name,
            str(before),
            str(after),
            str(saved),
            ratio_str,
            str(ms),
        ))

    total_pct = round((total_saved / total_before * 100), 1) if total_before > 0 else 0.0
    print(_sep())
    print(_row("TOTAL", str(total_before), str(total_after), str(total_saved), f"{total_pct:.1f}%", ""))
    print("╚" + "═" * total_inner + "╝")
    print()


def _print_compare_table(primary_results: list[dict], secondary_results: list[dict],
                          p_port: int, s_port: int) -> None:
    # Column widths: name=12, each port col=18, delta=8
    _cw = {"name": 12, "port": 18, "delta": 8}
    total_inner = (_cw["name"]+2) + (_cw["port"]+2) + (_cw["port"]+2) + (_cw["delta"]+2) + 3  # 3 inner seps

    def _csep(left="╠", mid="╬", right="╣"):
        segs = ["═"*(_cw["name"]+2), "═"*(_cw["port"]+2), "═"*(_cw["port"]+2), "═"*(_cw["delta"]+2)]
        return left + mid.join(segs) + right

    def _crow(name, p_col, s_col, delta):
        def _c(v, w): return f" {str(v)[:w].ljust(w)} "
        return "║" + "║".join([_c(name, _cw["name"]), _c(p_col, _cw["port"]),
                                _c(s_col, _cw["port"]), _c(delta, _cw["delta"])]) + "║"

    print()
    title = f" Compare: :{p_port} vs :{s_port} "
    print("╔" + "═" * total_inner + "╗")
    print("║" + title.center(total_inner) + "║")
    print(_csep("╠", "╦", "╣"))
    print(_crow("Payload", f":{p_port} saved / ratio", f":{s_port} saved / ratio", "Delta"))
    print(_csep())

    for p, s in zip(primary_results, secondary_results):
        name = p.get("_name", "?")
        pc = p.get("compression", {})
        sc = s.get("compression", {})
        p_saved = pc.get("tokens_saved", 0)
        s_saved = sc.get("tokens_saved", 0)
        p_pct = pc.get("reduction_pct", 0.0)
        s_pct = sc.get("reduction_pct", 0.0)
        delta = s_pct - p_pct
        print(_crow(name, f"{p_saved} / {p_pct:.1f}%", f"{s_saved} / {s_pct:.1f}%", f"{delta:+.1f}%"))

    print("╚" + "═" * total_inner + "╝")
    print()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_dry_run(port: int, directory: str | None = None) -> None:
    """Run all payloads through /v1/messages/dry-run and print results."""
    print(f"\nRunning benchmarks against port {port}...")
    results = []
    payloads = dict(PAYLOADS)

    # Add dynamic code-explorer scenario if a directory was specified (or default to claude-proxy dir)
    probe_dir = directory or str(Path(__file__).parent)
    sys.stdout.write(f"  building code-explorer ({Path(probe_dir).name}/)... ")
    sys.stdout.flush()
    explorer_msgs = _build_code_explorer_payload(probe_dir)
    payloads["code-explorer"] = explorer_msgs
    print("done")

    for name, messages in payloads.items():
        sys.stdout.write(f"  {name}... ")
        sys.stdout.flush()
        r = _dry_run_one(port, name, messages)
        results.append(r)
        if "_error" in r:
            print(f"ERROR: {r['_error']}")
        else:
            c = r.get("compression", {})
            print(f"{c.get('reduction_pct', 0):.1f}% saved")

    _print_table(results, port)


def cmd_compare(primary: int, secondary: int, directory: str | None = None) -> None:
    """Compare compression between two ports side-by-side."""
    print(f"\nComparing port {primary} vs port {secondary}...")
    primary_results = []
    secondary_results = []

    payloads = dict(PAYLOADS)
    probe_dir = directory or str(Path(__file__).parent)
    sys.stdout.write(f"  building code-explorer ({Path(probe_dir).name}/)... ")
    sys.stdout.flush()
    payloads["code-explorer"] = _build_code_explorer_payload(probe_dir)
    print("done")

    for name, messages in payloads.items():
        sys.stdout.write(f"  {name}... ")
        sys.stdout.flush()
        p = _dry_run_one(primary, name, messages)
        s = _dry_run_one(secondary, name, messages)
        primary_results.append(p)
        secondary_results.append(s)
        print("done")

    _print_compare_table(primary_results, secondary_results, primary, secondary)


def cmd_watch(port: int, interval: float) -> None:
    """Poll /metrics every N seconds and print live compression stats."""
    print(f"\nWatching port {port} (interval: {interval}s) — Ctrl+C to stop\n")

    def _bar(ratio: float, width: int = 20) -> str:
        filled = int(ratio * width)
        return "█" * filled + "░" * (width - filled)

    try:
        while True:
            data = _fetch_metrics(port)
            if data is None:
                print(f"\r  [!] Cannot reach port {port}", end="", flush=True)
                time.sleep(interval)
                continue

            c = data.get("compression", {})
            s = data.get("summary", {})
            ratio = c.get("avg_compression_ratio", 0.0)
            saved = c.get("total_tokens_saved", 0)
            requests = c.get("total_requests_compressed", 0)
            total_req = s.get("total_requests", 0)
            lag = data.get("current_lag_ms", 0.0)

            bar = _bar(ratio)
            ts = data.get("timestamp", "")[:19]

            print(
                f"\r  {ts}  "
                f"requests: {total_req:>6} (compressed: {requests:>5})  "
                f"saved: {saved:>8,} tokens  "
                f"ratio: {ratio*100:>5.1f}%  [{bar}]  "
                f"lag: {lag:.1f}ms     ",
                end="",
                flush=True,
            )
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\nStopped.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="stapler-compactor benchmarking CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_dry = sub.add_parser("dry-run", help="Run all payloads through dry-run endpoint")
    p_dry.add_argument("--port", type=int, default=47000)
    p_dry.add_argument("--dir", metavar="DIR", default=None,
                       help="Directory for code-explorer scenario (default: claude-proxy dir)")

    p_cmp = sub.add_parser("compare", help="Compare two proxy ports side-by-side")
    p_cmp.add_argument("--primary", type=int, default=47000)
    p_cmp.add_argument("--secondary", type=int, default=47001)
    p_cmp.add_argument("--dir", metavar="DIR", default=None,
                       help="Directory for code-explorer scenario (default: claude-proxy dir)")

    p_watch = sub.add_parser("watch", help="Live /metrics polling")
    p_watch.add_argument("--port", type=int, default=47000)
    p_watch.add_argument("--interval", type=float, default=2.0)

    args = parser.parse_args()

    if args.command == "dry-run":
        cmd_dry_run(args.port, args.dir)
    elif args.command == "compare":
        cmd_compare(args.primary, args.secondary, args.dir)
    elif args.command == "watch":
        cmd_watch(args.port, args.interval)


if __name__ == "__main__":
    main()
