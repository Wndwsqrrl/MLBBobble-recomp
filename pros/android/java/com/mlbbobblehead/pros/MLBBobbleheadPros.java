package com.mlbbobblehead.pros;

import android.os.Bundle;
import android.util.Log;
import android.view.WindowManager;

import java.io.File;
import java.util.ArrayList;

import org.libsdl.app.SDLActivity;

/**
 * SDL activity that runs the recompiled game (libmain.so, SDL_main).
 *
 * Game data lives in the app's external files directory, which adb can write
 * without any storage permission:
 *   files/game   - the Xbox 360 disc root (default.xex + data\, pushed with adb;
 *                  this build's data\ already carries the Oct-2011 roster update)
 *   files/user   - save data
 *   files/logs   - bobbleheadpros.log
 *
 * Push the data once with:
 *   adb push "<dump>\default.xex" /sdcard/Android/data/com.mlbbobblehead.pros/files/game/
 *   adb push "<dump>\data"        /sdcard/Android/data/com.mlbbobblehead.pros/files/game/
 */
public class MLBBobbleheadPros extends SDLActivity {
    private static final String TAG = "BobbleheadPros";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        try {
            // The game is landscape; keep SDL from ever creating a portrait window.
            android.system.Os.setenv("SDL_ORIENTATIONS", "LandscapeLeft LandscapeRight", true);
            // Pads arrive through Android input events; don't spin a core on HIDAPI/accelerometer.
            android.system.Os.setenv("SDL_ACCELEROMETER_AS_JOYSTICK", "0", true);
            android.system.Os.setenv("SDL_JOYSTICK_HIDAPI", "0", true);
        } catch (Exception e) {
            Log.w(TAG, "setenv: " + e);
        }
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    }

    @Override
    protected String[] getLibraries() {
        // SDL3 is linked statically into librexruntime.so, and libmain.so lists it
        // as a NEEDED dependency, so loading "main" pulls the runtime (and the SDL
        // JNI the Java layer calls) in with it. librexgpu-xenos.so is dlopen'd by
        // the runtime from the app's native library directory at startup.
        return new String[] { "main" };
    }

    @Override
    protected String[] getArguments() {
        File files = getExternalFilesDir(null);
        String root = files.getAbsolutePath();
        new File(files, "logs").mkdirs();
        new File(files, "user").mkdirs();

        ArrayList<String> args = new ArrayList<>();
        args.add("--game_data_root=" + root + "/game");
        args.add("--user_data_root=" + root + "/user");
        args.add("--gpu_plugin=xenos");
        // Full XBLA license (not the trial), as in bobbleheadpros.toml on the PC.
        args.add("--license_mask=1");
        args.add("--log_file=" + root + "/logs/bobbleheadpros.log");

        Log.i(TAG, "arguments: " + String.join(" ", args));
        return args.toArray(new String[0]);
    }
}
