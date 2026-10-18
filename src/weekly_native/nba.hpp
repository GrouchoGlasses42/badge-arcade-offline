#pragma once
#include <array>
#include <cstdint>
#include <functional>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace nba {
using Bytes = std::vector<uint8_t>;
using Progress = std::function<void(const std::string&, uint64_t, uint64_t)>;
constexpr uint64_t MAX_PACK = 128ULL * 1024 * 1024;

// A slice keeps archive members on disk; only small resource headers enter RAM.
struct Asset {
    std::string path;
    uint64_t offset = 0, size = 0;
    std::shared_ptr<const Bytes> memory;
    Bytes read(uint64_t start = 0, uint64_t length = UINT64_MAX) const;
    static Asset file(const std::string& path);
    static Asset generated(Bytes bytes);
    static Asset text(const std::string& text);
    Asset slice(uint64_t start, uint64_t length) const;
};
using Files = std::map<std::string, Asset>;
Files read_sarc(const Asset& archive);
void write_sarc(const Files& files, const std::string& path, const Progress& progress = {});
Bytes yaz0(const Asset& asset, size_t limit = SIZE_MAX);
Asset yaz0_literals(const Bytes& bytes);
uint32_t le32(const Bytes& b, size_t pos);
void put32(Bytes& b, size_t pos, uint32_t value);
std::string resource_name(const Bytes& b, size_t pos);

class Sha256 {
    std::array<uint32_t, 8> state_;
    std::array<uint8_t, 64> block_{};
    uint64_t length_ = 0;
    size_t used_ = 0;
    void compress();
public:
    Sha256();
    void update(const uint8_t* data, size_t size);
    std::array<uint8_t, 32> finish();
};
std::string sha256(const Asset& asset, const Progress& progress = {});
void write_file(const std::string& path, const Bytes& bytes);
void copy_file(const Asset& asset, const std::string& path, const Progress& progress = {});
void mkdirs(const std::string& path);
bool exists(const std::string& path);

struct Stage { std::string key, name; int first, last; };
struct Week { std::string start; Asset archive; std::vector<Stage> stages; };
Week read_week(const Asset& archive);
Asset read_allbadge(const Asset& archive);
struct Build {
    std::string base_archive, update_archive, schedule;
    std::shared_ptr<Week> week;
    std::shared_ptr<Asset> allbadge;
    bool home = false;
    bool verify_inputs = true;
};
struct Catalog { unsigned prizes = 0, machines = 0; std::string selection; };
Catalog build_content(const Build& request, const std::string& output, const Progress& progress = {});

}
