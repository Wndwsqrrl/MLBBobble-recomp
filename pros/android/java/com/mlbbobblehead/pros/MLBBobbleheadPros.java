package com.mlbbobblehead.pros;

import android.os.Bundle;
import android.view.WindowManager;

import java.io.File;

import org.libsdl.app.SDLActivity;

/**
 * Hosts the recompiled MLB Bobblehead Pros. SDLActivity loads libmain.so and
 * runs its SDL_main on a game thread; this class only says which libraries to
 * load and what command line to pass.
 *
 * The game files are not in the APK. Copy your own extracted game into the
 * app's external files folder (writable by adb, no storage permission needed):
 *
 *   Android/data/com.mlbbobblehead.pros/files/game/default.xex
 *   Android/data/com.mlbbobblehead.pros/files/game/data/...
 *
 * Saves go to files/user and the log to files/logs/bobbleheadpros.log.
 */
public class MLBBobbleheadPros extends SDLActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // A ballgame shouldn't dim the screen between pitches.
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    }

    @Override
    protected String[] getLibraries() {
        // libmain.so depends on the ReXGlue runtime libraries, so the system
        // linker loads them first; the Xenos GPU plugin is opened by the runtime.
        return new String[] { "main" };
    }

    @Override
    protected String[] getArguments() {
        File base = getExternalFilesDir(null);
        File logs = new File(base, "logs");
        File user = new File(base, "user");
        logs.mkdirs();
        user.mkdirs();
        return new String[] {
            "--game_data_root=" + new File(base, "game").getAbsolutePath(),
            "--user_data_root=" + user.getAbsolutePath(),
            "--log_file=" + new File(logs, "bobbleheadpros.log").getAbsolutePath(),
            "--gpu_plugin=xenos",
            "--license_mask=1",   // full game rather than the XBLA trial, as on the PC
        };
    }
}
