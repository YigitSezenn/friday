plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "com.friday.phone"
    compileSdk = 34
    defaultConfig {
        applicationId = "com.friday.phone"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "3.4"
    }
    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }
}
dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-ktx:1.9.1")
}
