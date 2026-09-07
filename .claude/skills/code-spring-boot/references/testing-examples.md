# Testing Code Examples

Layer overview and what/what-not to test lives in the main SKILL.md testing table. This file has the full worked examples per layer.

## Domain Tests — No Spring, No Mocks

```java
class OrderTest {

    @Test
    void cannot_cancel_shipped_order() {
        Order order = Order.create(CustomerId.generate(), List.of(anItem()));
        order.ship();

        assertThatThrownBy(order::cancel)
            .isInstanceOf(DomainException.class)
            .hasMessageContaining("Cannot cancel a shipped order");
    }

    @Test
    void total_sums_all_item_subtotals() {
        Order order = Order.create(CustomerId.generate(), List.of(
            OrderItem.of(productId, 2, Money.of("10.00", "USD")),
            OrderItem.of(productId, 1, Money.of("5.00", "USD"))
        ));

        assertThat(order.total()).isEqualTo(Money.of("25.00", "USD"));
    }
}
```

## Application Service Tests — Mockito

```java
@ExtendWith(MockitoExtension.class)
class OrderApplicationServiceTest {

    @Mock OrderRepository orderRepository;
    @Mock PaymentService paymentService;
    @InjectMocks OrderApplicationService sut;

    @Test
    void places_order_and_saves_it() {
        var cmd = new CreateOrderCommand(customerId, List.of(anItemDto()));
        when(customerRepository.findById(customerId)).thenReturn(Optional.of(aCustomer()));

        OrderId result = sut.placeOrder(cmd);

        assertThat(result).isNotNull();
        verify(orderRepository).save(any(Order.class));
    }
}
```

## Repository Tests — `@DataJpaTest`

```java
@DataJpaTest
class JpaOrderRepositoryTest {

    @Autowired OrderRepository orderRepository;  // The real JPA implementation

    @Test
    void finds_order_by_id() {
        Order saved = orderRepository.save(anOrder());
        Optional<Order> found = orderRepository.findById(saved.getId());
        assertThat(found).isPresent();
        assertThat(found.get().total()).isEqualTo(saved.total());
    }
}
```

## Testcontainers for Real DB

```java
@SpringBootTest
@Testcontainers
class OrderIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Test
    void full_order_placement_flow() { ... }
}
```
