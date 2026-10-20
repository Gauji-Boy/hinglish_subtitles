#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    // 1. Set current working directory to the folder containing this .exe
    char exePath[MAX_PATH];
    if (GetModuleFileNameA(NULL, exePath, MAX_PATH)) {
        char *lastSlash = strrchr(exePath, '\\');
        if (lastSlash) {
            *lastSlash = '\0';
            SetCurrentDirectoryA(exePath);
        }
    }

    // Set HF_HOME to D drive so all models download/cache on D:
    SetEnvironmentVariableA("HF_HOME", "D:\\Hinglish_subtitles\\models\\huggingface");

    // 2. Check launch_config.json to see if silent_launch is false
    int silent = 1;
    FILE *f = fopen("launch_config.json", "r");
    if (f) {
        char buf[512];
        size_t n = fread(buf, 1, sizeof(buf) - 1, f);
        buf[n] = '\0';
        fclose(f);
        if (strstr(buf, "\"silent_launch\": false")) {
            silent = 0;
        }
    }

    // 3. Locate Python executable (check D:\Python first, then PATH)
    char cmd[1024];
    const char *pythonExe = "pythonw.exe";
    const char *consoleExe = "python.exe";

    if (GetFileAttributesA("D:\\Python\\pythonw.exe") != INVALID_FILE_ATTRIBUTES) {
        pythonExe = "D:\\Python\\pythonw.exe";
    }
    if (GetFileAttributesA("D:\\Python\\python.exe") != INVALID_FILE_ATTRIBUTES) {
        consoleExe = "D:\\Python\\python.exe";
    }

    if (silent) {
        snprintf(cmd, sizeof(cmd), "\"%s\" server.py", pythonExe);
    } else {
        snprintf(cmd, sizeof(cmd), "\"%s\" server.py", consoleExe);
    }

    // 4. Spawn process
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));

    DWORD flags = silent ? CREATE_NO_WINDOW : CREATE_NEW_CONSOLE;

    if (CreateProcessA(NULL, cmd, NULL, NULL, FALSE, flags, NULL, NULL, &si, &pi)) {
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }

    return 0;
}
