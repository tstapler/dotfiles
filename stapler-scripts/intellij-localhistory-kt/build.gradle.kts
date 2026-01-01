plugins {
    kotlin("jvm") version "1.9.22"
    application
    id("org.graalvm.buildtools.native") version "0.10.4"
}

group = "com.stapler"
version = "1.0-SNAPSHOT"

repositories {
    mavenCentral()
    // JetBrains repositories for IntelliJ platform libraries
    maven("https://packages.jetbrains.team/maven/p/ij/intellij-dependencies")
    maven("https://www.jetbrains.com/intellij-repository/releases")
    maven("https://cache-redirector.jetbrains.com/intellij-dependencies")
}

dependencies {
    implementation("org.jetbrains.kotlin:kotlin-stdlib")
    // For command line parsing
    implementation("com.github.ajalt.clikt:clikt:4.2.1")

    // IntelliJ platform utilities for storage format parsing
    // Using intellij-platform-util which contains the io.storage classes
    implementation("com.jetbrains.intellij.platform:util:243.21565.208")

    // Needed for compression support
    implementation("org.lz4:lz4-java:1.8.0")

    // Testing dependencies
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.0")
    testImplementation("org.junit.jupiter:junit-jupiter-api:5.10.0")
    testRuntimeOnly("org.junit.jupiter:junit-jupiter-engine:5.10.0")
}

application {
    mainClass.set("com.stapler.localhistory.MainKt")
}

graalvmNative {
    binaries {
        named("main") {
            imageName.set("intellij-localhistory")
            mainClass.set("com.stapler.localhistory.MainKt")
            buildArgs.add("--no-fallback")
            buildArgs.add("-H:+ReportExceptionStackTraces")
        }
    }
}

tasks.jar {
    manifest {
        attributes["Main-Class"] = "com.stapler.localhistory.MainKt"
    }
    from(configurations.runtimeClasspath.get().map { if (it.isDirectory) it else zipTree(it) })
    duplicatesStrategy = DuplicatesStrategy.EXCLUDE
}

kotlin {
    jvmToolchain(17)
}

tasks.test {
    useJUnitPlatform()
}
