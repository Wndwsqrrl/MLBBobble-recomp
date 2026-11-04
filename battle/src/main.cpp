// bobbleheadbattle - ReXGlue Recompiled Project

#include "generated/default/bobbleheadbattle_init.h"

#include "bobbleheadbattle_app.h"

// Force the discrete GPU on hybrid (NVIDIA Optimus / AMD PowerXpress) laptops.
// The driver only honors these symbols when they are exported from the main
// executable, so they must live in the game exe, not the runtime DLL.
#if defined(_WIN32)
extern "C" {
__declspec(dllexport) unsigned long NvOptimusEnablement = 0x00000001;
__declspec(dllexport) int AmdPowerXpressRequestHighPerformance = 1;
}
#endif

REX_DEFINE_APP(bobbleheadbattle, BobbleheadbattleApp::Create)
