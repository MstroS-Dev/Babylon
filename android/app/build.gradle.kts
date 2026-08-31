plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.babylon.site"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.babylon.site"
        minSdk = 24
        targetSdk = 34
        // CI passes -PversionCode=<github.run_number> so every successful
        // Actions build gets a fresh, strictly-increasing version. Falls
        // back to 1 for local/manual builds where that isn't set.
        val ciVersionCode = (project.findProperty("versionCode") as String?)?.toIntOrNull() ?: 1
        versionCode = ciVersionCode
        versionName = "0.1.$ciVersionCode"
    }

    // AGP creates a "debug" signingConfig automatically, but by default it
    // points at an auto-generated, per-machine keystore. On GitHub Actions
    // that's a brand new keystore on every single run (fresh VM each time),
    // so every build had a different signature and Android refused to
    // install a new build as an "update" over the previous one - only a
    // full uninstall+reinstall worked. Pointing it at a fixed, checked-in
    // keystore instead makes every build share the same signature.
    signingConfigs {
        getByName("debug") {
            storeFile = file("debug.keystore")
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        viewBinding = true
        buildConfig = true
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("androidx.swiperefreshlayout:swiperefreshlayout:1.1.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.4")

    // ML Kit on-device translation (offline after language pack download)
    implementation("com.google.mlkit:translate:17.0.3")
    implementation("com.google.mlkit:language-id:17.0.6")

    // Networking to talk to our FastAPI server
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    // CameraX for before/after task photos
    implementation("androidx.camera:camera-core:1.3.4")
    implementation("androidx.camera:camera-camera2:1.3.4")
    implementation("androidx.camera:camera-lifecycle:1.3.4")
    implementation("androidx.camera:camera-view:1.3.4")

    // Image loading
    implementation("io.coil-kt:coil:2.6.0")
}
