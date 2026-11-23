# The map page calls these methods by name from JavaScript.
-keepclassmembers class app.mapwright.MapStore {
    @android.webkit.JavascriptInterface <methods>;
}
