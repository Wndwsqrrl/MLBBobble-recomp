// Guest-side hooks for MLB Bobblehead Pros.
// FIX: force XNetGetEthernetLinkStatus (wrapper 0x82291C94) to report an active link, else the
// game polls it forever at boot -> black screen. 0x0B = ACTIVE|100MBPS|FULL_DUPLEX.
#include <cstdio>
#include <atomic>
#include <mutex>
#include <rex/ppc/context.h>
namespace {
std::atomic<uint64_t> g_vblank{0};
std::mutex g_m;
std::FILE* tf(){ static std::FILE* f=std::fopen("F:/bobblehead-recomp/out/trace.log","w"); return f; }
}
void HookVblank(PPCRegister& r3){ uint64_t n=++g_vblank; if(n%600==0){ std::lock_guard<std::mutex> lk(g_m); auto f=tf(); if(f){std::fprintf(f,"vblank %llu\n",(unsigned long long)n); std::fflush(f);} } }
bool HookForceLink(PPCRegister& r3){ r3.u32=0x0B; return true; }
