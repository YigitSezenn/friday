plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "com.friday.phone"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.friday.phone"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "3.4"
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
}
dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-ktx:1.9.1")
    implementation("com.journeyapps:zxing-android-embedded:4.3.0")
}
