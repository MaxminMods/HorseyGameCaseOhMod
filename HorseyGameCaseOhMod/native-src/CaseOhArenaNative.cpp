#define WIN32_LEAN_AND_MEAN
#define NOMINMAX

#include <windows.h>
#include <windowsx.h>
#include <mmsystem.h>
#include <psapi.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cctype>
#include <cstdint>
#include <cstring>
#include <cwctype>
#include <iomanip>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")
#pragma comment(lib, "winmm.lib")
#pragma comment(lib, "psapi.lib")

namespace {

constexpr wchar_t kVersion[] = L"caseoh-1.0.0";
constexpr wchar_t kMarkerName[] = L".HorseyGameArenaBranch";
constexpr wchar_t kLogName[] = L"HorseyGameArenaNative.log";
constexpr wchar_t kSubOneRewardSound[] = L"Animal_HumanSmartAaron5.wav";
constexpr wchar_t kSubThreeRewardSound[] = L"Animal_HumanSmartAaron4.wav";
constexpr wchar_t kSteamInstallSuffix[] = L"\\steamapps\\common\\horsey game";
constexpr wchar_t kSteamDefault[] = L"c:\\program files (x86)\\steam\\steamapps\\common\\horsey game";

constexpr uintptr_t kHorseyImageBase = 0x140000000ull;
constexpr uintptr_t kHorseyTextFile = 0x00000400ull;
constexpr uintptr_t kHorseyTextVa = 0x140001000ull;
constexpr uintptr_t kHorseyRdataFile = 0x00300C00ull;
constexpr uintptr_t kHorseyRdataVa = 0x140302000ull;
constexpr uintptr_t kDistanceTableFileOff = 0x309B0Cull;
constexpr uintptr_t kDistanceLeaFileOff = 0x2CE0Bull;
constexpr uintptr_t kRestartStateOffsets[] = {0x2D727ull, 0x336D0ull};
constexpr uintptr_t kSoundEventFileOff = 0x3FFC0ull;

constexpr UINT_PTR kOverlayTimerId = 1;
constexpr UINT kOverlayTimerIntervalMs = 16;
constexpr int kRaceTimerHudWidth = 340;
constexpr int kRaceTimerHudHeight = 70;
constexpr DWORD kRaceReadyStartWindowMs = 12000;
constexpr uint64_t kNoHeldTimerMs = UINT64_MAX;

constexpr unsigned char kModulo4Sig[] = {
    0x8b, 0x83, 0x5c, 0x02, 0x00, 0x00, 0xff, 0xc0, 0x25, 0x03, 0x00, 0x00,
    0x80, 0x7d, 0x07, 0xff, 0xc8, 0x83, 0xc8, 0xfc, 0xff, 0xc0};
constexpr unsigned char kModulo5Patch[] = {
    0x8b, 0x83, 0x5c, 0x02, 0x00, 0x00, 0xff, 0xc0, 0x33, 0xd2, 0xb9, 0x05,
    0x00, 0x00, 0x00, 0xf7, 0xf1, 0x8b, 0xc2, 0x90, 0x90, 0x90};
constexpr unsigned char kLeaOriginal[] = {0x48, 0x8d, 0x0d, 0x16, 0x58, 0x2d, 0x00};
constexpr unsigned char kState4Assignment[] = {0x48, 0xc7, 0x83, 0x50, 0x02, 0x00, 0x00, 0x04, 0x00, 0x00, 0x00};
constexpr unsigned char kState5Assignment[] = {0x48, 0xc7, 0x83, 0x50, 0x02, 0x00, 0x00, 0x05, 0x00, 0x00, 0x00};
constexpr unsigned char kSoundEventPrologue[] = {0x48, 0x8b, 0xc4, 0x48, 0x89, 0x58, 0x18, 0x48, 0x89, 0x68, 0x20, 0x41, 0x56};
constexpr int kSoundEventPattern[] = {
    0x48, 0x8b, 0xc4, 0x48, 0x89, 0x58, 0x18, 0x48, 0x89, 0x68, 0x20, 0x41, 0x56,
    0x48, 0x83, 0xec, 0x70, 0x83, 0x3d, -1, -1, -1, -1, 0x00, 0x41, 0x8b, 0xe8,
    0x0f, 0x29, 0x70, 0xe8, 0x44, 0x8b, 0xf2, 0x0f, 0x28, 0xf3, 0x48, 0x8b, 0xd9,
    0x0f, 0x84, -1, -1, -1, -1, 0x80, 0x3d, -1, -1, -1, -1, 0x00, 0x0f, 0x85,
    -1, -1, -1, -1, 0x80, 0x3d, -1, -1, -1, -1, 0x00, 0x0f, 0x84, -1, -1, -1,
    -1, 0x48, 0x8b, 0xd1};
constexpr unsigned char kMapLabelOriginal[] = {
    'O', 'l', 'd', ' ', 'A', 'b', 'a', 'n', 'd', 'o', 'n', 'e', 'd', ' ', 'T', 'r', 'a', 'c', 'k'};
constexpr unsigned char kMapLabelPatched[] = {
    'T', 'h', 'e', ' ', 'C', 'a', 's', 'e', 'O', 'h', ' ', 'A', 'r', 'e', 'n', 'a', 0x00, 0x00, 0x00};

constexpr uint32_t kHorseyTimerEventReady = 1u << 0;
constexpr uint32_t kHorseyTimerEventStart = 1u << 1;
constexpr uint32_t kHorseyTimerEventFinish = 1u << 2;
constexpr uint32_t kHorseyTimerEventReset = 1u << 3;
constexpr uint32_t kHorseyTimerEventLocationExit = 1u << 4;

constexpr COLORREF kColorPanel = RGB(245, 246, 239);
constexpr COLORREF kColorInk = RGB(18, 20, 18);
constexpr COLORREF kColorGreen = RGB(0, 190, 80);
constexpr COLORREF kColorGreenDark = RGB(0, 92, 38);
constexpr COLORREF kColorCyan = RGB(0, 198, 214);
constexpr COLORREF kColorOrange = RGB(255, 142, 35);
constexpr COLORREF kColorMagenta = RGB(224, 38, 100);
constexpr COLORREF kTimerLightGreen = RGB(80, 235, 94);
constexpr COLORREF kTimerForestGreen = RGB(25, 142, 62);
constexpr COLORREF kTimerLightBlue = RGB(54, 182, 255);
constexpr COLORREF kTimerDarkBlue = RGB(40, 75, 214);
constexpr COLORREF kTimerLightPurple = RGB(170, 98, 255);
constexpr COLORREF kTimerDarkPurple = RGB(104, 42, 174);
constexpr COLORREF kTimerSlowOrange = RGB(242, 120, 28);
constexpr COLORREF kTimerRed = RGB(220, 34, 48);

HMODULE g_module = nullptr;
std::wstring g_game_dir;
std::wstring g_log_path;
HANDLE g_log = INVALID_HANDLE_VALUE;
std::mutex g_log_mutex;
std::atomic<bool> g_stop{false};

std::atomic<HWND> g_game_hwnd{nullptr};
std::atomic<HWND> g_overlay_hwnd{nullptr};
std::atomic<LONG_PTR> g_original_wndproc{0};
std::atomic<bool> g_game_window_resizing{false};

std::atomic<bool> g_overlay_visible{false};
std::atomic<bool> g_timer_running{false};
std::atomic<bool> g_race_timer_armed{false};
std::atomic<uint64_t> g_timer_started_at{0};
std::atomic<uint64_t> g_timer_elapsed_before_start{0};
std::atomic<uint64_t> g_timer_held_elapsed_ms{kNoHeldTimerMs};
std::atomic<DWORD> g_last_race_ready_tick{0};
std::atomic<DWORD> g_last_race_start_tick{0};
std::atomic<DWORD> g_last_race_finish_tick{0};
std::atomic<DWORD> g_last_reset_click_tick{0};
std::atomic<uint32_t> g_horsey_timer_event_flags{0};
std::atomic<uint64_t> g_horsey_ready_at_ms{0};
std::atomic<uint64_t> g_horsey_start_at_ms{0};
std::atomic<uint64_t> g_horsey_finish_at_ms{0};
std::atomic<uint64_t> g_horsey_reset_at_ms{0};
std::atomic<uint64_t> g_horsey_location_exit_at_ms{0};
std::atomic<bool> g_horsey_sound_event_hooked{false};
void* g_horsey_sound_event_trampoline = nullptr;

HFONT g_label_font = nullptr;

std::wstring ToLower(std::wstring value) {
    std::transform(value.begin(), value.end(), value.begin(), [](wchar_t ch) {
        return static_cast<wchar_t>(::towlower(ch));
    });
    return value;
}

std::string LowerAscii(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char ch) {
        return static_cast<char>(std::tolower(ch));
    });
    return value;
}

std::string WideToUtf8(const std::wstring& value) {
    if (value.empty()) {
        return {};
    }
    const int bytes = WideCharToMultiByte(CP_UTF8, 0, value.c_str(), static_cast<int>(value.size()), nullptr, 0, nullptr, nullptr);
    if (bytes <= 0) {
        return {};
    }
    std::string out(static_cast<size_t>(bytes), '\0');
    WideCharToMultiByte(CP_UTF8, 0, value.c_str(), static_cast<int>(value.size()), out.data(), bytes, nullptr, nullptr);
    return out;
}

std::wstring Utf8ToWide(const std::string& value) {
    if (value.empty()) {
        return {};
    }
    const int chars = MultiByteToWideChar(CP_UTF8, 0, value.data(), static_cast<int>(value.size()), nullptr, 0);
    if (chars <= 0) {
        return {};
    }
    std::wstring out(static_cast<size_t>(chars), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, value.data(), static_cast<int>(value.size()), out.data(), chars);
    return out;
}

std::wstring DirName(const std::wstring& path) {
    const size_t pos = path.find_last_of(L"\\/");
    return pos == std::wstring::npos ? L"." : path.substr(0, pos);
}

std::wstring BaseName(const std::wstring& path) {
    const size_t pos = path.find_last_of(L"\\/");
    return pos == std::wstring::npos ? path : path.substr(pos + 1);
}

std::wstring TrimTrailingSlashes(std::wstring value) {
    while (value.size() > 3 && (value.back() == L'\\' || value.back() == L'/')) {
        value.pop_back();
    }
    return value;
}

std::wstring PathJoin(const std::wstring& left, const std::wstring& right) {
    if (left.empty()) {
        return right;
    }
    if (right.empty()) {
        return left;
    }
    if (left.back() == L'\\' || left.back() == L'/') {
        return left + right;
    }
    return left + L"\\" + right;
}

bool FileExists(const std::wstring& path) {
    const DWORD attrs = GetFileAttributesW(path.c_str());
    return attrs != INVALID_FILE_ATTRIBUTES && (attrs & FILE_ATTRIBUTE_DIRECTORY) == 0;
}

std::wstring HexUInt(uint64_t value) {
    std::wstringstream ss;
    ss << L"0x" << std::hex << std::uppercase << value;
    return ss.str();
}

std::wstring HexPtr(const void* ptr) {
    return HexUInt(reinterpret_cast<uintptr_t>(ptr));
}

std::wstring SanitizeForLog(std::wstring value, size_t max_chars = 360) {
    for (wchar_t& ch : value) {
        if (ch == L'\r' || ch == L'\n' || ch == L'\t') {
            ch = L' ';
        }
        if (ch < 32) {
            ch = L'.';
        }
    }
    if (value.size() > max_chars) {
        value.resize(max_chars);
        value += L"...";
    }
    return value;
}

void DebugLine(const std::wstring& line) {
    OutputDebugStringW((L"[CaseOhArenaNative] " + line + L"\n").c_str());
}

void LogLine(const std::wstring& category, const std::wstring& message) {
    SYSTEMTIME st{};
    GetLocalTime(&st);
    std::wstringstream ss;
    ss << std::setfill(L'0')
       << std::setw(4) << st.wYear << L"-"
       << std::setw(2) << st.wMonth << L"-"
       << std::setw(2) << st.wDay << L" "
       << std::setw(2) << st.wHour << L":"
       << std::setw(2) << st.wMinute << L":"
       << std::setw(2) << st.wSecond << L"."
       << std::setw(3) << st.wMilliseconds
       << L" [" << category << L"] " << SanitizeForLog(message) << L"\r\n";

    const std::wstring line = ss.str();
    DebugLine(line);
    std::lock_guard<std::mutex> lock(g_log_mutex);
    if (g_log == INVALID_HANDLE_VALUE) {
        return;
    }
    const std::string utf8 = WideToUtf8(line);
    DWORD written = 0;
    WriteFile(g_log, utf8.data(), static_cast<DWORD>(utf8.size()), &written, nullptr);
    FlushFileBuffers(g_log);
}

uintptr_t RvaFromFileOffset(uintptr_t file_off) {
    if (file_off >= kHorseyTextFile && file_off < kHorseyRdataFile) {
        return (kHorseyTextVa - kHorseyImageBase) + (file_off - kHorseyTextFile);
    }
    if (file_off >= kHorseyRdataFile) {
        return (kHorseyRdataVa - kHorseyImageBase) + (file_off - kHorseyRdataFile);
    }
    return 0;
}

bool RuntimeWriteBytes(void* target, const void* data, size_t size) {
    DWORD old_protect = 0;
    if (!VirtualProtect(target, size, PAGE_EXECUTE_READWRITE, &old_protect)) {
        return false;
    }
    memcpy(target, data, size);
    FlushInstructionCache(GetCurrentProcess(), target, size);
    DWORD ignored = 0;
    VirtualProtect(target, size, old_protect, &ignored);
    return true;
}

bool RuntimeBytesEqual(const unsigned char* addr, const unsigned char* expected, size_t size) {
    return memcmp(addr, expected, size) == 0;
}

bool RuntimeBytesZero(const unsigned char* addr, size_t size) {
    for (size_t i = 0; i < size; ++i) {
        if (addr[i] != 0) {
            return false;
        }
    }
    return true;
}

unsigned char* FindRuntimeSignature(unsigned char* base, size_t size, const unsigned char* sig, size_t sig_size, int* hits_out) {
    int hits = 0;
    unsigned char* found = nullptr;
    if (!base || sig_size == 0 || size < sig_size) {
        if (hits_out) {
            *hits_out = 0;
        }
        return nullptr;
    }
    for (size_t i = 0; i <= size - sig_size; ++i) {
        if (memcmp(base + i, sig, sig_size) == 0) {
            ++hits;
            found = base + i;
        }
    }
    if (hits_out) {
        *hits_out = hits;
    }
    return hits == 1 ? found : nullptr;
}

unsigned char* FindRuntimePattern(unsigned char* base, size_t size, const int* pattern, size_t pattern_size, int* hits_out) {
    int hits = 0;
    unsigned char* found = nullptr;
    if (!base || pattern_size == 0 || size < pattern_size) {
        if (hits_out) {
            *hits_out = 0;
        }
        return nullptr;
    }
    for (size_t i = 0; i <= size - pattern_size; ++i) {
        bool ok = true;
        for (size_t j = 0; j < pattern_size; ++j) {
            const int expected = pattern[j];
            if (expected >= 0 && base[i + j] != static_cast<unsigned char>(expected)) {
                ok = false;
                break;
            }
        }
        if (ok) {
            ++hits;
            found = base + i;
        }
    }
    if (hits_out) {
        *hits_out = hits;
    }
    return hits == 1 ? found : nullptr;
}

bool RuntimeAddressFromFileOffset(unsigned char* module_base, size_t module_size, uintptr_t file_off, unsigned char** out) {
    const uintptr_t rva = RvaFromFileOffset(file_off);
    if (rva == 0 || rva >= module_size) {
        return false;
    }
    *out = module_base + rva;
    return true;
}

void MakeDistanceTableBytes(float a, float b, float c, float d, float e, unsigned char (&out)[20]) {
    const float values[5] = {a, b, c, d, e};
    memcpy(out, values, sizeof(values));
}

bool ApplyRuntimeCaseohArenaPatch() {
    HMODULE module = GetModuleHandleW(nullptr);
    MODULEINFO info{};
    if (!module || !GetModuleInformation(GetCurrentProcess(), module, &info, sizeof(info))) {
        LogLine(L"runtime-patch", L"skipped: could not read Horsey module information");
        return false;
    }
    auto* base = static_cast<unsigned char*>(info.lpBaseOfDll);
    const size_t module_size = static_cast<size_t>(info.SizeOfImage);
    bool ok = true;
    int hits = 0;

    if (FindRuntimeSignature(base, module_size, kModulo5Patch, sizeof(kModulo5Patch), &hits) && hits == 1) {
        LogLine(L"runtime-patch", L"selector modulo already patched");
    } else {
        unsigned char* modulo = FindRuntimeSignature(base, module_size, kModulo4Sig, sizeof(kModulo4Sig), &hits);
        if (modulo && hits == 1 && RuntimeWriteBytes(modulo, kModulo5Patch, sizeof(kModulo5Patch))) {
            LogLine(L"runtime-patch", L"selector modulo patched at " + HexPtr(modulo));
        } else {
            LogLine(L"runtime-patch", L"selector modulo not patched; signature count " + std::to_wstring(hits));
            ok = false;
        }
    }

    for (uintptr_t off : kRestartStateOffsets) {
        unsigned char* addr = nullptr;
        if (!RuntimeAddressFromFileOffset(base, module_size, off, &addr)) {
            ok = false;
            continue;
        }
        if (RuntimeBytesEqual(addr, kState4Assignment, sizeof(kState4Assignment))) {
            LogLine(L"runtime-patch", L"restart state already vanilla at file " + HexUInt(off));
        } else if (RuntimeBytesEqual(addr, kState5Assignment, sizeof(kState5Assignment))) {
            if (RuntimeWriteBytes(addr, kState4Assignment, sizeof(kState4Assignment))) {
                LogLine(L"runtime-patch", L"restart state repaired at file " + HexUInt(off));
            } else {
                ok = false;
            }
        } else {
            LogLine(L"runtime-patch", L"restart state signature unknown at file " + HexUInt(off));
            ok = false;
        }
    }

    unsigned char table_bytes[20]{};
    unsigned char old_table_a[20]{};
    unsigned char old_table_b[20]{};
    MakeDistanceTableBytes(25.0f, 37.0f, 60.0f, 120.0f, 12.0f, table_bytes);
    MakeDistanceTableBytes(25.0f, 37.0f, 60.0f, 12.0f, 120.0f, old_table_a);
    MakeDistanceTableBytes(25.0f, 37.0f, 60.0f, 12.0f, 1200.0f, old_table_b);

    unsigned char* table_addr = nullptr;
    if (RuntimeAddressFromFileOffset(base, module_size, kDistanceTableFileOff, &table_addr)) {
        const bool known_table =
            RuntimeBytesEqual(table_addr, table_bytes, sizeof(table_bytes)) ||
            RuntimeBytesEqual(table_addr, old_table_a, sizeof(old_table_a)) ||
            RuntimeBytesEqual(table_addr, old_table_b, sizeof(old_table_b)) ||
            RuntimeBytesZero(table_addr, sizeof(table_bytes));
        if (!known_table) {
            LogLine(L"runtime-patch", L"distance table contains unknown data; not patching");
            ok = false;
        } else if (RuntimeBytesEqual(table_addr, table_bytes, sizeof(table_bytes))) {
            LogLine(L"runtime-patch", L"distance table already patched");
        } else if (RuntimeWriteBytes(table_addr, table_bytes, sizeof(table_bytes))) {
            LogLine(L"runtime-patch", L"distance table patched at " + HexPtr(table_addr));
        } else {
            ok = false;
        }
    } else {
        ok = false;
    }

    if (table_addr) {
        unsigned char* lea = FindRuntimeSignature(base, module_size, kLeaOriginal, sizeof(kLeaOriginal), &hits);
        if (lea && hits == 1) {
            const intptr_t disp64 = reinterpret_cast<intptr_t>(table_addr) - static_cast<intptr_t>(reinterpret_cast<uintptr_t>(lea) + sizeof(kLeaOriginal));
            if (disp64 >= INT32_MIN && disp64 <= INT32_MAX) {
                unsigned char new_lea[7] = {0x48, 0x8d, 0x0d, 0, 0, 0, 0};
                const int32_t disp32 = static_cast<int32_t>(disp64);
                memcpy(new_lea + 3, &disp32, sizeof(disp32));
                if (RuntimeWriteBytes(lea, new_lea, sizeof(new_lea))) {
                    LogLine(L"runtime-patch", L"distance table pointer patched at " + HexPtr(lea));
                } else {
                    ok = false;
                }
            } else {
                ok = false;
            }
        } else {
            unsigned char* known_lea = nullptr;
            if (RuntimeAddressFromFileOffset(base, module_size, kDistanceLeaFileOff, &known_lea) && known_lea[0] == 0x48 && known_lea[1] == 0x8d && known_lea[2] == 0x0d) {
                int32_t disp32 = 0;
                memcpy(&disp32, known_lea + 3, sizeof(disp32));
                unsigned char* target = known_lea + 7 + disp32;
                if (target == table_addr) {
                    LogLine(L"runtime-patch", L"distance table pointer already patched");
                } else {
                    ok = false;
                }
            } else {
                ok = false;
            }
        }
    }

    if (FindRuntimeSignature(base, module_size, kMapLabelPatched, sizeof(kMapLabelPatched), &hits) && hits == 1) {
        LogLine(L"runtime-patch", L"world map label already patched");
    } else {
        unsigned char* label = FindRuntimeSignature(base, module_size, kMapLabelOriginal, sizeof(kMapLabelOriginal), &hits);
        if (label && hits == 1 && RuntimeWriteBytes(label, kMapLabelPatched, sizeof(kMapLabelPatched))) {
            LogLine(L"runtime-patch", L"world map label patched at " + HexPtr(label));
        } else {
            LogLine(L"runtime-patch", L"world map label already handled by branch files or not present at runtime");
        }
    }

    LogLine(L"runtime-patch", ok ? L"CaseOh Arena runtime patch ready" : L"CaseOh Arena runtime patch incomplete");
    return ok;
}

uint64_t NowMs() {
    static LARGE_INTEGER frequency{};
    static LARGE_INTEGER baseline{};
    static const bool ready = []() {
        return QueryPerformanceFrequency(&frequency) && QueryPerformanceCounter(&baseline);
    }();
    if (!ready || frequency.QuadPart <= 0) {
        return static_cast<uint64_t>(GetTickCount64());
    }
    LARGE_INTEGER now{};
    QueryPerformanceCounter(&now);
    const long double elapsed_ticks = static_cast<long double>(now.QuadPart - baseline.QuadPart);
    const long double elapsed_ms = elapsed_ticks * 1000.0L / static_cast<long double>(frequency.QuadPart);
    return static_cast<uint64_t>(elapsed_ms);
}

std::wstring FormatDuration(uint64_t ms) {
    const uint64_t total_seconds = ms / 1000;
    const uint64_t minutes = total_seconds / 60;
    const uint64_t seconds = total_seconds % 60;
    const uint64_t milliseconds = ms % 1000;
    std::wstringstream ss;
    ss << std::setfill(L'0') << std::setw(2) << minutes << L":"
       << std::setw(2) << seconds << L"." << std::setw(3) << milliseconds;
    return ss.str();
}

uint64_t TimerElapsedAt(uint64_t now_ms) {
    const bool running = g_timer_running.load();
    const uint64_t held = g_timer_held_elapsed_ms.load();
    if (!running && held != kNoHeldTimerMs) {
        return held;
    }
    uint64_t elapsed = g_timer_elapsed_before_start.load();
    if (running) {
        const uint64_t started_at = g_timer_started_at.load();
        if (now_ms >= started_at) {
            elapsed += now_ms - started_at;
        }
    }
    return elapsed;
}

uint64_t TimerElapsedMs() {
    return TimerElapsedAt(NowMs());
}

void ShowOverlayNow() {
    g_overlay_visible.store(true);
    HWND overlay = g_overlay_hwnd.load();
    if (overlay && IsWindow(overlay)) {
        ShowWindow(overlay, SW_SHOWNOACTIVATE);
        InvalidateRect(overlay, nullptr, FALSE);
    }
}

void HideOverlayNow() {
    g_overlay_visible.store(false);
    HWND overlay = g_overlay_hwnd.load();
    if (overlay && IsWindow(overlay)) {
        ShowWindow(overlay, SW_HIDE);
        InvalidateRect(overlay, nullptr, TRUE);
    }
}

void ClearRaceTimerArm() {
    g_race_timer_armed.store(false);
    g_last_race_ready_tick.store(0);
}

void StartTimerAt(uint64_t start_ms) {
    ClearRaceTimerArm();
    g_timer_elapsed_before_start.store(0);
    g_timer_held_elapsed_ms.store(kNoHeldTimerMs);
    g_timer_started_at.store(start_ms);
    g_timer_running.store(true);
    g_last_race_start_tick.store(GetTickCount());
    ShowOverlayNow();
}

void StopTimerKeepElapsedAt(uint64_t stop_ms) {
    if (!g_timer_running.load()) {
        return;
    }
    const uint64_t elapsed = TimerElapsedAt(stop_ms);
    g_timer_elapsed_before_start.store(elapsed);
    g_timer_held_elapsed_ms.store(elapsed);
    g_timer_started_at.store(0);
    g_timer_running.store(false);
    ShowOverlayNow();
}

void ResetTimerQuiet() {
    ClearRaceTimerArm();
    g_timer_running.store(false);
    g_timer_started_at.store(0);
    g_timer_elapsed_before_start.store(0);
    g_timer_held_elapsed_ms.store(kNoHeldTimerMs);
    HideOverlayNow();
}

void PlayFastFinishRewardIfNeeded(uint64_t elapsed_ms) {
    if (elapsed_ms >= 3000 || g_game_dir.empty()) {
        return;
    }
    const wchar_t* reward_sound = elapsed_ms < 1000 ? kSubOneRewardSound : kSubThreeRewardSound;
    const std::wstring path = PathJoin(PathJoin(g_game_dir, L"sound"), reward_sound);
    PlaySoundW(path.c_str(), nullptr, SND_FILENAME | SND_ASYNC | SND_NODEFAULT);
}

void ArmRaceTimerFromGameSignal(const std::wstring& source) {
    if (g_timer_running.load()) {
        return;
    }
    const DWORD now = GetTickCount();
    g_last_race_ready_tick.store(now);
    g_race_timer_armed.store(true);
    g_timer_held_elapsed_ms.store(kNoHeldTimerMs);
    ShowOverlayNow();
    LogLine(L"timer", L"armed from " + source + L"; waiting for RaceGo");
}

void StartRaceTimerFromGameSignalAt(const std::wstring& source, uint64_t start_ms) {
    if (g_timer_running.load()) {
        return;
    }
    const DWORD now = GetTickCount();
    const DWORD ready = g_last_race_ready_tick.load();
    if (!g_race_timer_armed.load() || ready == 0 || (now - ready) > kRaceReadyStartWindowMs) {
        LogLine(L"timer", L"ignored RaceGo because no recent ready/get-set event was seen");
        ClearRaceTimerArm();
        return;
    }
    StartTimerAt(start_ms);
    LogLine(L"timer", L"auto-started from " + source);
}

void StopRaceTimerFromGameSignalAt(const std::wstring& source, uint64_t stop_ms) {
    if (!g_timer_running.load()) {
        return;
    }
    if (TimerElapsedAt(stop_ms) < 150) {
        return;
    }
    const DWORD now = GetTickCount();
    const DWORD last = g_last_race_finish_tick.load();
    if ((now - last) < 2500) {
        return;
    }
    g_last_race_finish_tick.store(now);
    StopTimerKeepElapsedAt(stop_ms);
    const uint64_t elapsed = TimerElapsedMs();
    PlayFastFinishRewardIfNeeded(elapsed);
    LogLine(L"timer", L"auto-stopped from " + source + L" at " + FormatDuration(elapsed));
}

void ResetRaceTimerFromGameSignal(const std::wstring& source) {
    const uint64_t stop_ms = NowMs();
    const bool was_running = g_timer_running.load();
    const uint64_t elapsed = TimerElapsedAt(stop_ms);
    if (!was_running && elapsed == 0) {
        ClearRaceTimerArm();
        return;
    }
    ClearRaceTimerArm();
    g_timer_elapsed_before_start.store(elapsed);
    g_timer_held_elapsed_ms.store(elapsed);
    g_timer_started_at.store(0);
    g_timer_running.store(false);
    ShowOverlayNow();
    LogLine(L"timer", L"auto-stopped and held from " + source + L" at " + FormatDuration(elapsed));
}

void HideRaceTimerForLocationExit(const std::wstring& source) {
    ResetTimerQuiet();
    LogLine(L"timer", L"hid timer from " + source);
}

void QueueHorseyTimerEvent(uint32_t flag, std::atomic<uint64_t>& timestamp_slot) {
    timestamp_slot.store(NowMs());
    g_horsey_timer_event_flags.fetch_or(flag);
}

std::string ReadHorseyStdString(void* string_object) {
    if (!string_object) {
        return {};
    }
    const auto* base = static_cast<const unsigned char*>(string_object);
    const size_t size = *reinterpret_cast<const size_t*>(base + 0x10);
    const size_t capacity = *reinterpret_cast<const size_t*>(base + 0x18);
    if (size == 0 || size > 128) {
        return {};
    }
    const char* text = capacity <= 15
        ? reinterpret_cast<const char*>(base)
        : *reinterpret_cast<const char* const*>(base);
    if (!text) {
        return {};
    }
    std::string out(text, text + size);
    for (char ch : out) {
        const unsigned char c = static_cast<unsigned char>(ch);
        if (c < 0x20 || c > 0x7e) {
            return {};
        }
    }
    return out;
}

void HandleHorseySoundEvent(const std::string& event_name) {
    if (event_name.empty()) {
        return;
    }
    const std::string lower = LowerAscii(event_name);
    if (g_timer_running.load() || g_race_timer_armed.load() || g_timer_held_elapsed_ms.load() != kNoHeldTimerMs) {
        LogLine(L"sound-event", L"Horsey sound/event while timer visible: " + Utf8ToWide(event_name));
    }

    if (lower.find("onyourmark") != std::string::npos || lower.find("getset") != std::string::npos) {
        QueueHorseyTimerEvent(kHorseyTimerEventReady, g_horsey_ready_at_ms);
        return;
    }
    if (lower.find("startnextrace") != std::string::npos ||
        lower.find("returntotrack") != std::string::npos ||
        lower.find("restart") != std::string::npos) {
        QueueHorseyTimerEvent(kHorseyTimerEventReset, g_horsey_reset_at_ms);
        return;
    }
    if (lower.find("racego") != std::string::npos || lower.find("startrace") != std::string::npos) {
        QueueHorseyTimerEvent(kHorseyTimerEventStart, g_horsey_start_at_ms);
        return;
    }
    if (lower.find("crossfinishline") != std::string::npos) {
        QueueHorseyTimerEvent(kHorseyTimerEventFinish, g_horsey_finish_at_ms);
        return;
    }
    if (lower.find("truckleavelocation") != std::string::npos ||
        lower.find("leavelocation") != std::string::npos ||
        lower.find("truckmotor") != std::string::npos ||
        lower.find("balloon") != std::string::npos ||
        lower.find("grabdisk") != std::string::npos ||
        lower.find("enterlocationbiohacker") != std::string::npos) {
        QueueHorseyTimerEvent(kHorseyTimerEventLocationExit, g_horsey_location_exit_at_ms);
    }
}

void ProcessHorseyTimerEvents() {
    const uint32_t flags = g_horsey_timer_event_flags.exchange(0);
    if (flags == 0) {
        return;
    }
    if ((flags & kHorseyTimerEventReady) != 0) {
        g_horsey_ready_at_ms.exchange(0);
        ArmRaceTimerFromGameSignal(L"Horsey ready internal event");
    }
    if ((flags & kHorseyTimerEventStart) != 0) {
        const uint64_t start_ms = g_horsey_start_at_ms.exchange(0);
        StartRaceTimerFromGameSignalAt(L"Horsey RaceGo bell", start_ms == 0 ? NowMs() : start_ms);
    }
    if ((flags & kHorseyTimerEventFinish) != 0) {
        const uint64_t finish_ms = g_horsey_finish_at_ms.exchange(0);
        StopRaceTimerFromGameSignalAt(L"Horsey first finish whistle", finish_ms == 0 ? NowMs() : finish_ms);
    }
    if ((flags & kHorseyTimerEventReset) != 0) {
        g_horsey_reset_at_ms.exchange(0);
        ResetRaceTimerFromGameSignal(L"Horsey restart/reset");
    }
    if ((flags & kHorseyTimerEventLocationExit) != 0) {
        g_horsey_location_exit_at_ms.exchange(0);
        HideRaceTimerForLocationExit(L"Horsey location/map event");
    }
}

void __fastcall HorseySoundEventNotify(void* sound_name) {
    static thread_local bool inside_hook = false;
    if (!inside_hook) {
        inside_hook = true;
        HandleHorseySoundEvent(ReadHorseyStdString(sound_name));
        inside_hook = false;
    }
}

void AppendImm32(std::vector<unsigned char>& code, uint32_t value) {
    for (int i = 0; i < 4; ++i) {
        code.push_back(static_cast<unsigned char>((value >> (i * 8)) & 0xff));
    }
}

void AppendImm64(std::vector<unsigned char>& code, uintptr_t value) {
    for (int i = 0; i < 8; ++i) {
        code.push_back(static_cast<unsigned char>((value >> (i * 8)) & 0xff));
    }
}

void AppendBytes(std::vector<unsigned char>& code, std::initializer_list<unsigned char> bytes) {
    code.insert(code.end(), bytes.begin(), bytes.end());
}

std::vector<unsigned char> BuildPassThroughSoundHookStub(unsigned char* continue_at) {
    std::vector<unsigned char> code;
    code.reserve(192);
    AppendBytes(code, {0x48, 0x81, 0xEC}); AppendImm32(code, 0xA8);
    AppendBytes(code, {0x48, 0x89, 0x4C, 0x24, 0x20});
    AppendBytes(code, {0x48, 0x89, 0x54, 0x24, 0x28});
    AppendBytes(code, {0x4C, 0x89, 0x44, 0x24, 0x30});
    AppendBytes(code, {0x4C, 0x89, 0x4C, 0x24, 0x38});
    AppendBytes(code, {0xF3, 0x0F, 0x7F, 0x44, 0x24, 0x40});
    AppendBytes(code, {0xF3, 0x0F, 0x7F, 0x4C, 0x24, 0x50});
    AppendBytes(code, {0xF3, 0x0F, 0x7F, 0x54, 0x24, 0x60});
    AppendBytes(code, {0xF3, 0x0F, 0x7F, 0x5C, 0x24, 0x70});
    AppendBytes(code, {0x48, 0xB8}); AppendImm64(code, reinterpret_cast<uintptr_t>(&HorseySoundEventNotify));
    AppendBytes(code, {0xFF, 0xD0});
    AppendBytes(code, {0xF3, 0x0F, 0x6F, 0x44, 0x24, 0x40});
    AppendBytes(code, {0xF3, 0x0F, 0x6F, 0x4C, 0x24, 0x50});
    AppendBytes(code, {0xF3, 0x0F, 0x6F, 0x54, 0x24, 0x60});
    AppendBytes(code, {0xF3, 0x0F, 0x6F, 0x5C, 0x24, 0x70});
    AppendBytes(code, {0x4C, 0x8B, 0x4C, 0x24, 0x38});
    AppendBytes(code, {0x4C, 0x8B, 0x44, 0x24, 0x30});
    AppendBytes(code, {0x48, 0x8B, 0x54, 0x24, 0x28});
    AppendBytes(code, {0x48, 0x8B, 0x4C, 0x24, 0x20});
    AppendBytes(code, {0x48, 0x81, 0xC4}); AppendImm32(code, 0xA8);
    AppendBytes(code, {0x48, 0x8B, 0xC4});
    AppendBytes(code, {0x48, 0x89, 0x58, 0x18});
    AppendBytes(code, {0x48, 0x89, 0x68, 0x20});
    AppendBytes(code, {0x41, 0x56});
    AppendBytes(code, {0x49, 0xBB}); AppendImm64(code, reinterpret_cast<uintptr_t>(continue_at));
    AppendBytes(code, {0x41, 0xFF, 0xE3});
    return code;
}

bool WriteAbsoluteJumpBytes(unsigned char* target, const void* destination, size_t patch_size) {
    std::array<unsigned char, 16> patch{};
    patch[0] = 0x48;
    patch[1] = 0xB8;
    const uintptr_t dest = reinterpret_cast<uintptr_t>(destination);
    memcpy(patch.data() + 2, &dest, sizeof(dest));
    patch[10] = 0xFF;
    patch[11] = 0xE0;
    for (size_t i = 12; i < patch_size; ++i) {
        patch[i] = 0x90;
    }
    return RuntimeWriteBytes(target, patch.data(), patch_size);
}

bool InstallHorseySoundEventHook() {
    if (g_horsey_sound_event_hooked.load()) {
        return true;
    }
    HMODULE horsey = GetModuleHandleW(nullptr);
    MODULEINFO info{};
    if (!horsey || !GetModuleInformation(GetCurrentProcess(), horsey, &info, sizeof(info))) {
        LogLine(L"timer-hook", L"sound event hook skipped: could not read Horsey module information");
        return false;
    }
    auto* base = static_cast<unsigned char*>(info.lpBaseOfDll);
    const size_t module_size = static_cast<size_t>(info.SizeOfImage);
    constexpr size_t patch_size = sizeof(kSoundEventPrologue);
    unsigned char* target = nullptr;
    std::wstring target_source = L"known offset";
    if (RuntimeAddressFromFileOffset(base, module_size, kSoundEventFileOff, &target) &&
        RuntimeBytesEqual(target, kSoundEventPrologue, patch_size)) {
        target_source = L"known offset";
    } else {
        int hits = 0;
        target = FindRuntimePattern(base, module_size, kSoundEventPattern, sizeof(kSoundEventPattern) / sizeof(kSoundEventPattern[0]), &hits);
        if (!target || !RuntimeBytesEqual(target, kSoundEventPrologue, patch_size)) {
            LogLine(L"timer-hook", L"sound event hook skipped: pattern scan found " + std::to_wstring(hits) + L" candidate(s)");
            return false;
        }
        target_source = L"pattern scan";
    }

    std::vector<unsigned char> stub = BuildPassThroughSoundHookStub(target + patch_size);
    auto* stub_code = static_cast<unsigned char*>(VirtualAlloc(nullptr, stub.size(), MEM_RESERVE | MEM_COMMIT, PAGE_EXECUTE_READWRITE));
    if (!stub_code) {
        LogLine(L"timer-hook", L"sound event hook skipped: stub allocation failed");
        return false;
    }
    memcpy(stub_code, stub.data(), stub.size());
    FlushInstructionCache(GetCurrentProcess(), stub_code, stub.size());
    if (!WriteAbsoluteJumpBytes(target, stub_code, patch_size)) {
        VirtualFree(stub_code, 0, MEM_RELEASE);
        LogLine(L"timer-hook", L"sound event hook skipped: target patch failed");
        return false;
    }
    g_horsey_sound_event_trampoline = stub_code;
    g_horsey_sound_event_hooked.store(true);
    LogLine(L"timer-hook", L"installed CaseOh timer sound/event hook by " + target_source + L" at " + HexPtr(target));
    return true;
}

BOOL CALLBACK EnumWindowsForProcess(HWND hwnd, LPARAM lparam) {
    DWORD pid = 0;
    GetWindowThreadProcessId(hwnd, &pid);
    if (pid != GetCurrentProcessId() || !IsWindowVisible(hwnd)) {
        return TRUE;
    }
    *reinterpret_cast<HWND*>(lparam) = hwnd;
    return FALSE;
}

HWND FindGameWindow() {
    HWND hwnd = nullptr;
    EnumWindows(EnumWindowsForProcess, reinterpret_cast<LPARAM>(&hwnd));
    return hwnd;
}

bool ClientPointLooksLikeRaceResetControl(HWND hwnd, POINT pt) {
    RECT client{};
    if (!GetClientRect(hwnd, &client)) {
        return false;
    }
    const int width = std::max(0L, client.right - client.left);
    const int height = std::max(0L, client.bottom - client.top);
    if (width <= 0 || height <= 0) {
        return false;
    }
    const int top_limit = std::min(110, std::max(72, height / 8));
    return pt.x >= 0 && pt.y >= 0 && pt.x <= width && pt.y <= top_limit;
}

std::wstring DescribeMousePoint(HWND hwnd, UINT message, LPARAM lparam) {
    POINT client{GET_X_LPARAM(lparam), GET_Y_LPARAM(lparam)};
    POINT screen = client;
    ClientToScreen(hwnd, &screen);
    std::wstringstream ss;
    ss << L"message=" << HexUInt(message)
       << L" screen=(" << screen.x << L"," << screen.y << L")"
       << L" client=(" << client.x << L"," << client.y << L")";
    return ss.str();
}

void MaybeStopTimerFromRaceResetClick(HWND hwnd, UINT message, LPARAM lparam) {
    if ((message != WM_LBUTTONDOWN && message != WM_LBUTTONUP) || !g_timer_running.load()) {
        return;
    }
    if (TimerElapsedMs() < 150) {
        return;
    }
    POINT pt{GET_X_LPARAM(lparam), GET_Y_LPARAM(lparam)};
    if (!ClientPointLooksLikeRaceResetControl(hwnd, pt)) {
        return;
    }
    const DWORD now = GetTickCount();
    const DWORD last = g_last_reset_click_tick.load();
    if ((now - last) < 1000) {
        return;
    }
    g_last_reset_click_tick.store(now);
    LogLine(L"timer-click", L"reset matched from Horsey top command band " + DescribeMousePoint(hwnd, message, lparam));
    ResetRaceTimerFromGameSignal(L"Horsey reset-button click");
}

LRESULT CALLBACK GameWndProc(HWND hwnd, UINT message, WPARAM wparam, LPARAM lparam) {
    if (message == WM_ENTERSIZEMOVE || message == WM_SIZING) {
        g_game_window_resizing.store(true);
    } else if (message == WM_EXITSIZEMOVE) {
        g_game_window_resizing.store(false);
    }
    if (message == WM_LBUTTONDOWN || message == WM_LBUTTONUP) {
        MaybeStopTimerFromRaceResetClick(hwnd, message, lparam);
    }
    const auto original = reinterpret_cast<WNDPROC>(g_original_wndproc.load());
    LRESULT result = original ? CallWindowProcW(original, hwnd, message, wparam, lparam) : DefWindowProcW(hwnd, message, wparam, lparam);
    if (message == WM_NCDESTROY && hwnd == g_game_hwnd.load()) {
        g_game_window_resizing.store(false);
        g_game_hwnd.store(nullptr);
        g_original_wndproc.store(0);
        LogLine(L"window-hook", L"game window destroyed; hook state cleared");
    }
    return result;
}

bool InstallWindowHook() {
    if (g_original_wndproc.load() != 0 && IsWindow(g_game_hwnd.load())) {
        return true;
    }
    HWND hwnd = FindGameWindow();
    if (!hwnd) {
        return false;
    }
    SetLastError(0);
    const LONG_PTR previous = SetWindowLongPtrW(hwnd, GWLP_WNDPROC, reinterpret_cast<LONG_PTR>(GameWndProc));
    if (previous == 0 && GetLastError() != 0) {
        LogLine(L"window-hook", L"SetWindowLongPtrW failed for hwnd=" + HexPtr(hwnd));
        return false;
    }
    g_game_hwnd.store(hwnd);
    g_original_wndproc.store(previous);
    LogLine(L"window-hook", L"installed reset-click hook hwnd=" + HexPtr(hwnd));
    return true;
}

void FillSolidRect(HDC dc, const RECT& rc, COLORREF color) {
    HBRUSH brush = CreateSolidBrush(color);
    FillRect(dc, &rc, brush);
    DeleteObject(brush);
}

void DrawPixelFrame(HDC dc, const RECT& rc, COLORREF fill, COLORREF border, int thickness) {
    FillSolidRect(dc, rc, border);
    RECT inner{rc.left + thickness, rc.top + thickness, rc.right - thickness, rc.bottom - thickness};
    FillSolidRect(dc, inner, fill);
}

const char* PixelGlyphRow(wchar_t ch, int row) {
    static const char* zero[] = {"111", "101", "101", "101", "111"};
    static const char* one[] = {"010", "110", "010", "010", "111"};
    static const char* two[] = {"111", "001", "111", "100", "111"};
    static const char* three[] = {"111", "001", "111", "001", "111"};
    static const char* four[] = {"101", "101", "111", "001", "001"};
    static const char* five[] = {"111", "100", "111", "001", "111"};
    static const char* six[] = {"111", "100", "111", "101", "111"};
    static const char* seven[] = {"111", "001", "001", "001", "001"};
    static const char* eight[] = {"111", "101", "111", "101", "111"};
    static const char* nine[] = {"111", "101", "111", "001", "111"};
    static const char* colon[] = {"0", "1", "0", "1", "0"};
    static const char* dot[] = {"0", "0", "0", "0", "1"};
    static const char* blank[] = {"0", "0", "0", "0", "0"};

    switch (ch) {
        case L'0': return zero[row];
        case L'1': return one[row];
        case L'2': return two[row];
        case L'3': return three[row];
        case L'4': return four[row];
        case L'5': return five[row];
        case L'6': return six[row];
        case L'7': return seven[row];
        case L'8': return eight[row];
        case L'9': return nine[row];
        case L':': return colon[row];
        case L'.': return dot[row];
        default: return blank[row];
    }
}

int PixelGlyphWidth(wchar_t ch) {
    return (ch == L':' || ch == L'.' || ch == L' ') ? 1 : 3;
}

int PixelTextWidth(const std::wstring& text, int scale, int gap) {
    int width = 0;
    for (wchar_t ch : text) {
        width += PixelGlyphWidth(ch) * scale + gap;
    }
    return text.empty() ? 0 : width - gap;
}

void DrawPixelText(HDC dc, const std::wstring& text, int x, int y, int scale, int gap, COLORREF color) {
    int cursor = x;
    for (wchar_t ch : text) {
        const int glyph_width = PixelGlyphWidth(ch);
        for (int row = 0; row < 5; ++row) {
            const char* pattern = PixelGlyphRow(ch, row);
            for (int col = 0; col < glyph_width; ++col) {
                if (pattern[col] != '1') {
                    continue;
                }
                RECT block{
                    cursor + col * scale,
                    y + row * scale,
                    cursor + (col + 1) * scale - 1,
                    y + (row + 1) * scale - 1};
                FillSolidRect(dc, block, color);
            }
        }
        cursor += glyph_width * scale + gap;
    }
}

COLORREF RainbowTimerColor(int index, uint64_t speed_ms) {
    static constexpr COLORREF kRainbow[] = {
        RGB(226, 32, 48), RGB(255, 128, 32), RGB(255, 220, 48),
        RGB(58, 220, 78), RGB(70, 190, 255), RGB(103, 36, 185), RGB(226, 48, 196)};
    const uint64_t step = std::max<uint64_t>(1, speed_ms);
    const size_t offset = static_cast<size_t>((NowMs() / step) % _countof(kRainbow));
    return kRainbow[(static_cast<size_t>(index) + offset) % _countof(kRainbow)];
}

COLORREF StaticRainbowTimerColor(int index) {
    static constexpr COLORREF kRainbow[] = {
        RGB(226, 32, 48), RGB(255, 128, 32), RGB(255, 220, 48),
        RGB(58, 220, 78), RGB(70, 190, 255), RGB(103, 36, 185), RGB(226, 48, 196)};
    return kRainbow[static_cast<size_t>(index) % _countof(kRainbow)];
}

COLORREF FinishedTimerDigitColor(uint64_t elapsed_ms, int index) {
    if (elapsed_ms < 1000) return RainbowTimerColor(index * 2, 90);
    if (elapsed_ms <= 3000) return StaticRainbowTimerColor(index);
    if (elapsed_ms < 5000) return kTimerLightGreen;
    if (elapsed_ms < 7000) return kTimerForestGreen;
    if (elapsed_ms < 10000) return kTimerLightBlue;
    if (elapsed_ms < 15000) return kTimerDarkBlue;
    if (elapsed_ms < 20000) return kTimerLightPurple;
    if (elapsed_ms < 30000) return kTimerDarkPurple;
    if (elapsed_ms < 60000) return kTimerSlowOrange;
    return kTimerRed;
}

void DrawFinishedTimerPixelText(HDC dc, const std::wstring& text, int x, int y, int scale, int gap, uint64_t elapsed_ms) {
    int cursor = x;
    int glyph_index = 0;
    for (wchar_t ch : text) {
        const int glyph_width = PixelGlyphWidth(ch);
        const COLORREF color = FinishedTimerDigitColor(elapsed_ms, glyph_index);
        for (int row = 0; row < 5; ++row) {
            const char* pattern = PixelGlyphRow(ch, row);
            for (int col = 0; col < glyph_width; ++col) {
                if (pattern[col] != '1') {
                    continue;
                }
                RECT block{
                    cursor + col * scale,
                    y + row * scale,
                    cursor + (col + 1) * scale - 1,
                    y + (row + 1) * scale - 1};
                FillSolidRect(dc, block, color);
            }
        }
        cursor += glyph_width * scale + gap;
        ++glyph_index;
    }
}

void DrawRaceTimerSign(HDC dc, const RECT& rc) {
    const bool finished = !g_timer_running.load() && g_timer_held_elapsed_ms.load() != kNoHeldTimerMs;
    const bool armed = g_race_timer_armed.load();
    const uint64_t elapsed_ms = TimerElapsedMs();
    const std::wstring duration = FormatDuration(elapsed_ms);
    const COLORREF border = finished ? kColorMagenta : kColorGreen;
    const COLORREF digit_color = finished ? FinishedTimerDigitColor(elapsed_ms, 0) : kColorInk;
    const COLORREF shadow = finished ? RGB(96, 0, 120) : kColorGreenDark;

    DrawPixelFrame(dc, rc, kColorPanel, border, 4);
    RECT stripe{rc.left + 10, rc.top + 10, rc.left + 18, rc.bottom - 10};
    FillSolidRect(dc, stripe, finished ? kColorOrange : kColorCyan);

    RECT label_rc{rc.left + 28, rc.top + 8, rc.left + 112, rc.top + 30};
    SetBkMode(dc, TRANSPARENT);
    SetTextColor(dc, kColorInk);
    HFONT old_font = static_cast<HFONT>(SelectObject(dc, g_label_font ? g_label_font : GetStockObject(DEFAULT_GUI_FONT)));
    DrawTextW(dc, finished ? L"FINISH" : (armed ? L"READY" : L"RACE"), -1, &label_rc, DT_LEFT | DT_TOP | DT_SINGLELINE | DT_NOPREFIX);

    RECT face{rc.left + 112, rc.top + 10, rc.right - 12, rc.bottom - 10};
    DrawPixelFrame(dc, face, RGB(255, 255, 250), kColorGreenDark, 3);
    const int scale = 7;
    const int gap = 4;
    const int digit_width = PixelTextWidth(duration, scale, gap);
    const int face_width = static_cast<int>(face.right - face.left);
    const int face_height = static_cast<int>(face.bottom - face.top);
    const int digit_x = static_cast<int>(face.left) + std::max(0, (face_width - digit_width) / 2);
    const int digit_y = static_cast<int>(face.top) + std::max(0, (face_height - 5 * scale) / 2);
    DrawPixelText(dc, duration, digit_x + 2, digit_y + 2, scale, gap, shadow);
    if (finished) {
        DrawFinishedTimerPixelText(dc, duration, digit_x, digit_y, scale, gap, elapsed_ms);
    } else {
        DrawPixelText(dc, duration, digit_x, digit_y, scale, gap, digit_color);
    }
    SelectObject(dc, old_font);
}

LRESULT CALLBACK OverlayWndProc(HWND hwnd, UINT message, WPARAM wparam, LPARAM lparam) {
    switch (message) {
        case WM_NCHITTEST:
            return HTTRANSPARENT;
        case WM_ERASEBKGND:
            return 1;
        case WM_TIMER:
            if (wparam == kOverlayTimerId) {
                InvalidateRect(hwnd, nullptr, FALSE);
            }
            return 0;
        case WM_PAINT: {
            PAINTSTRUCT ps{};
            HDC dc = BeginPaint(hwnd, &ps);
            RECT rc{};
            GetClientRect(hwnd, &rc);
            if (g_overlay_visible.load()) {
                DrawRaceTimerSign(dc, rc);
            }
            EndPaint(hwnd, &ps);
            return 0;
        }
        case WM_DESTROY:
            KillTimer(hwnd, kOverlayTimerId);
            return 0;
        default:
            return DefWindowProcW(hwnd, message, wparam, lparam);
    }
}

bool CreateOverlayWindow() {
    WNDCLASSEXW wc{};
    wc.cbSize = sizeof(wc);
    wc.lpfnWndProc = OverlayWndProc;
    wc.hInstance = g_module;
    wc.hCursor = LoadCursor(nullptr, IDC_ARROW);
    wc.lpszClassName = L"CaseOhArenaTimerOverlay";
    RegisterClassExW(&wc);

    HWND owner = FindGameWindow();
    if (owner) {
        g_game_hwnd.store(owner);
    }
    HWND hwnd = CreateWindowExW(
        WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TRANSPARENT,
        wc.lpszClassName,
        L"CaseOh Arena Timer",
        WS_POPUP,
        CW_USEDEFAULT,
        CW_USEDEFAULT,
        kRaceTimerHudWidth,
        kRaceTimerHudHeight,
        owner,
        nullptr,
        g_module,
        nullptr);
    if (!hwnd) {
        LogLine(L"overlay", L"CreateWindowExW failed");
        return false;
    }
    g_overlay_hwnd.store(hwnd);
    SetLayeredWindowAttributes(hwnd, 0, 232, LWA_ALPHA);
    g_label_font = CreateFontW(17, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS,
        CLIP_DEFAULT_PRECIS, DEFAULT_QUALITY, DEFAULT_PITCH | FF_SWISS, L"Segoe UI");
    SetTimer(hwnd, kOverlayTimerId, kOverlayTimerIntervalMs, nullptr);
    ShowWindow(hwnd, SW_HIDE);
    LogLine(L"overlay", L"created CaseOh timer-only overlay");
    return true;
}

bool ForegroundIsOurs() {
    HWND fg = GetForegroundWindow();
    if (!fg) {
        return false;
    }
    DWORD pid = 0;
    GetWindowThreadProcessId(fg, &pid);
    return pid == GetCurrentProcessId();
}

void UpdateOverlayPosition() {
    HWND overlay = g_overlay_hwnd.load();
    if (!overlay) {
        return;
    }
    HWND target = g_game_hwnd.load();
    if (!target || !IsWindow(target)) {
        target = FindGameWindow();
        if (target) {
            g_game_hwnd.store(target);
        }
    }
    if (!target || !g_overlay_visible.load() || !ForegroundIsOurs() || g_game_window_resizing.load()) {
        ShowWindow(overlay, SW_HIDE);
        return;
    }
    if (GetWindow(overlay, GW_OWNER) != target) {
        SetWindowLongPtrW(overlay, GWLP_HWNDPARENT, reinterpret_cast<LONG_PTR>(target));
    }
    RECT rect{};
    if (!GetWindowRect(target, &rect)) {
        ShowWindow(overlay, SW_HIDE);
        return;
    }
    const int width = kRaceTimerHudWidth;
    const int height = kRaceTimerHudHeight;
    const int x = rect.left + ((rect.right - rect.left) - width) / 2;
    const int y = rect.top + 28;
    SetWindowPos(overlay, HWND_TOP, x, y, width, height, SWP_SHOWWINDOW | SWP_NOACTIVATE);
}

bool OpenBranchLog() {
    const std::wstring save_dir = PathJoin(g_game_dir, L"save");
    CreateDirectoryW(save_dir.c_str(), nullptr);
    g_log_path = PathJoin(save_dir, kLogName);
    g_log = CreateFileW(g_log_path.c_str(), FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        nullptr, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (g_log == INVALID_HANDLE_VALUE) {
        DebugLine(L"refusing: could not open branch log at " + g_log_path);
        return false;
    }
    return true;
}

bool IsSteamInstallPath(const std::wstring& path) {
    const std::wstring lower = ToLower(TrimTrailingSlashes(path));
    return lower == kSteamDefault || lower.size() >= wcslen(kSteamInstallSuffix) &&
        lower.compare(lower.size() - wcslen(kSteamInstallSuffix), wcslen(kSteamInstallSuffix), kSteamInstallSuffix) == 0;
}

bool SafetyCheck() {
    std::array<wchar_t, 32768> exe_path{};
    const DWORD len = GetModuleFileNameW(nullptr, exe_path.data(), static_cast<DWORD>(exe_path.size()));
    if (len == 0 || len >= exe_path.size()) {
        DebugLine(L"refusing: could not resolve host executable path");
        return false;
    }
    if (ToLower(BaseName(exe_path.data())) != L"horsey.exe") {
        DebugLine(L"refusing: host executable is not Horsey.exe");
        return false;
    }
    g_game_dir = TrimTrailingSlashes(DirName(exe_path.data()));
    if (IsSteamInstallPath(g_game_dir)) {
        DebugLine(L"refusing: normal Steam install path detected");
        return false;
    }
    const std::wstring marker = PathJoin(g_game_dir, kMarkerName);
    if (!FileExists(marker)) {
        DebugLine(L"refusing: missing branch marker " + marker);
        return false;
    }
    if (!OpenBranchLog()) {
        return false;
    }
    LogLine(L"startup", L"CaseOh-only HorseyGameArenaNative " + std::wstring(kVersion) + L" loaded");
    LogLine(L"safety-pass", L"branch marker ok; multiplayer UI is not included in this runtime");
    return true;
}

DWORD WINAPI MainThread(void*) {
    if (!SafetyCheck()) {
        return 0;
    }
    NowMs();
    ApplyRuntimeCaseohArenaPatch();
    InstallHorseySoundEventHook();
    CreateOverlayWindow();

    DWORD last_hook_attempt = 0;
    while (!g_stop.load()) {
        MSG msg{};
        while (PeekMessageW(&msg, nullptr, 0, 0, PM_REMOVE)) {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
        ProcessHorseyTimerEvents();
        UpdateOverlayPosition();
        const DWORD now = GetTickCount();
        if ((now - last_hook_attempt) > 1000) {
            last_hook_attempt = now;
            InstallWindowHook();
        }
        Sleep(16);
    }
    return 0;
}

} // namespace

BOOL APIENTRY DllMain(HMODULE module, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        g_module = module;
        DisableThreadLibraryCalls(module);
        HANDLE thread = CreateThread(nullptr, 0, MainThread, nullptr, 0, nullptr);
        if (thread) {
            CloseHandle(thread);
        }
    } else if (reason == DLL_PROCESS_DETACH) {
        g_stop.store(true);
        if (g_label_font) {
            DeleteObject(g_label_font);
            g_label_font = nullptr;
        }
        if (g_log != INVALID_HANDLE_VALUE) {
            CloseHandle(g_log);
            g_log = INVALID_HANDLE_VALUE;
        }
    }
    return TRUE;
}
