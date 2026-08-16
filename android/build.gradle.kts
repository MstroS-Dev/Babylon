buildscript {
    repositories {
        google()
        mavenCentral()
    }
    dependencies {
        classpath("com.android.tools.build:gradle:8.5.2")
        classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:1.9.24")
    }
}

// No allprojects { repositories {...} } block here on purpose - settings.gradle.kts
// already centralizes repos via dependencyResolutionManagement with
// FAIL_ON_PROJECT_REPOS, which forbids any project build file from declaring its
// own repositories too. (This is what broke every prior CI build: an "allprojects"
// block here duplicated google()/mavenCentral(), which Gradle rejects outright
// when that mode is set.)
