#include "nba.hpp"
#include <algorithm>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <sys/stat.h>
#include <unistd.h>

namespace nba {
namespace {
// An explicit pointer type avoids GCC warnings about glibc's fclose attributes.
using File = std::unique_ptr<FILE, int (*)(FILE*)>;
File open(const std::string& path, const char* mode) {
    FILE* f = fopen(path.c_str(), mode);
    if (!f) throw std::runtime_error("Cannot open " + path + ": " + strerror(errno));
    return File(f, fclose);
}
void read_exact(FILE* f, void* out, size_t size) {
    if (fread(out, 1, size, f) != size) throw std::runtime_error("Truncated input file");
}
void write_exact(FILE* f, const void* in, size_t size) {
    if (fwrite(in, 1, size, f) != size) throw std::runtime_error("File write failed (check free space)");
}
void seek(FILE* f, uint64_t offset) {
    if (offset > INT32_MAX || fseek(f, static_cast<long>(offset), SEEK_SET))
        throw std::runtime_error("Invalid file offset");
}
uint32_t ror(uint32_t x, unsigned n) { return (x >> n) | (x << (32 - n)); }
uint32_t be32(const uint8_t* p) { return uint32_t(p[0]) << 24 | uint32_t(p[1]) << 16 | uint32_t(p[2]) << 8 | p[3]; }
}
Asset Asset::file(const std::string& path) {
    struct stat st{};
    if (stat(path.c_str(), &st) || !S_ISREG(st.st_mode) || st.st_size < 0)
        throw std::runtime_error("Missing input file: " + path);
    return {path, 0, static_cast<uint64_t>(st.st_size), {}};
}
Asset Asset::generated(Bytes bytes) {
    auto ptr = std::make_shared<const Bytes>(std::move(bytes));
    return {"", 0, ptr->size(), ptr};
}
Asset Asset::text(const std::string& text) { return generated(Bytes(text.begin(), text.end())); }
Asset Asset::slice(uint64_t start, uint64_t length) const {
    if (start > size || length > size - start) throw std::runtime_error("Archive member is outside file");
    auto result = *this; result.offset += start; result.size = length; return result;
}
Bytes Asset::read(uint64_t start, uint64_t length) const {
    if (start > size) throw std::runtime_error("Read outside archive member");
    length = std::min(length, size - start);
    if (length > 8 * 1024 * 1024) throw std::runtime_error("Resource exceeds memory limit");
    Bytes out(static_cast<size_t>(length));
    if (memory) {
        if (offset + start + length > memory->size()) throw std::runtime_error("Invalid memory slice");
        std::copy_n(memory->data() + offset + start, length, out.data());
    } else {
        auto f = open(path, "rb"); seek(f.get(), offset + start); read_exact(f.get(), out.data(), out.size());
    }
    return out;
}
uint32_t le32(const Bytes& b, size_t pos) {
    if (pos > b.size() || b.size() - pos < 4) throw std::runtime_error("Truncated resource header");
    return b[pos] | uint32_t(b[pos+1]) << 8 | uint32_t(b[pos+2]) << 16 | uint32_t(b[pos+3]) << 24;
}
void put32(Bytes& b, size_t pos, uint32_t value) {
    if (pos > b.size() || b.size() - pos < 4) throw std::runtime_error("Invalid output header");
    for (unsigned i = 0; i < 4; ++i) b[pos+i] = value >> (8*i);
}
std::string resource_name(const Bytes& b, size_t pos) {
    if (pos > b.size() || b.size() - pos < 48) throw std::runtime_error("Truncated resource name");
    std::string value;
    for (size_t i = pos; i < pos + 48 && b[i]; ++i) {
        char c = b[i];
        if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.'))
            throw std::runtime_error("Unsafe resource name");
        value += c;
    }
    if (value.empty() || value.size() > 47 || value=="." || value.find("..")!=std::string::npos)
        throw std::runtime_error("Invalid resource name");
    return value;
}
bool exists(const std::string& path) { struct stat st{}; return lstat(path.c_str(), &st) == 0; }
void mkdirs(const std::string& path) {
    if (path.empty() || exists(path)) return;
    const size_t slash = path.find_last_of('/');
    if (slash != std::string::npos && slash > 0) mkdirs(path.substr(0, slash));
    if (mkdir(path.c_str(), 0777) && errno != EEXIST) throw std::runtime_error("Cannot create directory: " + path);
}
void write_file(const std::string& path, const Bytes& bytes) {
    mkdirs(path.substr(0, path.find_last_of('/')));
    auto f = open(path, "wb"); write_exact(f.get(), bytes.data(), bytes.size());
    if (fflush(f.get()) || fsync(fileno(f.get()))) throw std::runtime_error("Cannot flush output file: " + path);
}
void copy_file(const Asset& asset, const std::string& path, const Progress& progress) {
    mkdirs(path.substr(0, path.find_last_of('/')));
    auto f = open(path, "wb");
    File source(nullptr, fclose);
    if (!asset.memory) { source = open(asset.path, "rb"); seek(source.get(), asset.offset); }
    Bytes block(65536);
    for (uint64_t done = 0; done < asset.size;) {
        size_t count = std::min<uint64_t>(block.size(), asset.size - done);
        if (source) read_exact(source.get(), block.data(), count);
        else std::copy_n(asset.memory->data() + asset.offset + done, count, block.data());
        write_exact(f.get(), block.data(), count); done += count;
        if (progress) progress("Writing patch files", done, asset.size);
    }
    if (fflush(f.get()) || fsync(fileno(f.get()))) throw std::runtime_error("Cannot flush output file");
}

Files read_sarc(const Asset& archive) {
    auto head = archive.read(0, 32);
    if (head.size() != 32 || memcmp(head.data(), "SARC", 4) || head[6] != 0xff || head[7] != 0xfe
        || le32(head, 8) != archive.size || memcmp(head.data()+20, "SFAT", 4))
        throw std::runtime_error("Invalid little-endian SARC");
    const uint32_t data = le32(head, 12);
    const unsigned count = head[26] | unsigned(head[27]) << 8;
    const uint32_t names = 40 + count * 16;
    if (data < names || data > archive.size || data > 2*1024*1024) throw std::runtime_error("Invalid SARC index");
    auto index = archive.read(0, data);
    if (memcmp(index.data() + names - 8, "SFNT", 4)) throw std::runtime_error("Invalid SARC name table");
    Files out;
    for (unsigned i = 0; i < count; ++i) {
        uint32_t attr = le32(index, 36 + i*16);
        uint64_t pos = names + uint64_t(attr & 0xffffff) * 4;
        uint64_t first = le32(index, 40 + i*16), last = le32(index, 44 + i*16);
        if ((attr >> 24) != 1 || pos >= data || first > last || last > archive.size-data)
            throw std::runtime_error("Invalid SARC member");
        std::string name;
        while (pos < data && index[pos]) name += char(index[pos++]);
        if (pos == data || name.empty() || name.size() > 255 || name.front() == '/' || name.find("..") != std::string::npos
            || name.find('\\') != std::string::npos || name.find(':') != std::string::npos)
            throw std::runtime_error("Unsafe SARC member name");
        if (!out.emplace(name, archive.slice(data + first, last - first)).second)
            throw std::runtime_error("Duplicate SARC member");
    }
    return out;
}
void write_sarc(const Files& files, const std::string& path, const Progress& progress) {
    // Native SARC index heap is 256 KiB; reserve space for allocator overhead.
    if (files.size() * 16 > 0x3f000) throw std::runtime_error("Catalog exceeds native archive index capacity");
    struct Member { uint32_t hash, name; const std::pair<const std::string, Asset>* file; };
    std::vector<Member> members;
    for (const auto& file : files) {
        uint32_t hash = 0; for (uint8_t c : file.first) hash = hash * 101 + c;
        members.push_back({hash, 0, &file});
    }
    std::sort(members.begin(), members.end(), [](const Member& a, const Member& b) {
        return a.hash == b.hash ? a.file->first < b.file->first : a.hash < b.hash;
    });
    Bytes names;
    for (auto& m : members) {
        m.name = names.size()/4;
        names.insert(names.end(), m.file->first.begin(), m.file->first.end()); names.push_back(0);
        while (names.size() % 4) names.push_back(0);
    }
    uint32_t data = (40 + members.size()*16 + names.size() + 127) & ~127U;
    Bytes header(data);
    memcpy(header.data(), "SARC", 4); header[4] = 20; header[6] = 0xff; header[7] = 0xfe;
    put32(header, 12, data); header[17] = 1;
    memcpy(header.data()+20, "SFAT", 4); header[24] = 12;
    header[26] = members.size(); header[27] = members.size() >> 8; put32(header, 28, 101);
    size_t sfnt = 32 + members.size()*16;
    memcpy(header.data()+sfnt, "SFNT", 4); header[sfnt+4] = 8;
    std::copy(names.begin(), names.end(), header.begin()+sfnt+8);
    uint64_t end = 0;
    for (unsigned i = 0; i < members.size(); ++i) {
        end = (end + 127) & ~127ULL;
        put32(header, 32+i*16, members[i].hash); put32(header, 36+i*16, 0x1000000 | members[i].name);
        put32(header, 40+i*16, end); end += members[i].file->second.size;
        if (end + data > MAX_PACK) throw std::runtime_error("Generated catalog exceeds supported archive size");
        put32(header, 44+i*16, end);
    }
    put32(header, 8, data+end);
    mkdirs(path.substr(0, path.find_last_of('/')));
    auto f = open(path, "wb"); write_exact(f.get(), header.data(), header.size());
    uint64_t written = 0; Bytes buffer(65536), zeros(128);
    for (unsigned i = 0; i < members.size(); ++i) {
        uint64_t start = le32(header, 40+i*16);
        write_exact(f.get(), zeros.data(), start-written); written = start;
        const auto& asset = members[i].file->second;
        File source(nullptr, fclose);
        if (!asset.memory) { source = open(asset.path, "rb"); seek(source.get(), asset.offset); }
        for (uint64_t done = 0; done < asset.size;) {
            size_t length = std::min<uint64_t>(buffer.size(), asset.size-done);
            if (source) read_exact(source.get(), buffer.data(), length);
            else std::copy_n(asset.memory->data()+asset.offset+done, length, buffer.data());
            write_exact(f.get(), buffer.data(), length); done += length; written += length;
        }
        if (progress && i % 16 == 0) progress("Building game catalog", i, members.size());
    }
    if (fflush(f.get()) || fsync(fileno(f.get()))) throw std::runtime_error("Cannot flush generated catalog");
}
Bytes yaz0(const Asset& asset, size_t limit) {
    auto head = asset.read(0, 16);
    if (head.size() != 16 || memcmp(head.data(), "Yaz0", 4)) throw std::runtime_error("Invalid Yaz0 resource");
    uint32_t size = be32(head.data()+4);
    if (size > 8*1024*1024) throw std::runtime_error("Oversized Yaz0 resource");
    size = std::min<size_t>(size, limit);
    Bytes out; out.reserve(size); Bytes cache; uint64_t cursor = 16, cache_start = 0;
    auto next = [&]() -> uint8_t {
        if (cursor >= asset.size) throw std::runtime_error("Truncated Yaz0 stream");
        if (cache.empty() || cursor < cache_start || cursor >= cache_start+cache.size()) {
            cache_start = cursor; cache = asset.read(cursor, 4096);
        }
        return cache[cursor++ - cache_start];
    };
    while (out.size() < size) {
        uint8_t flags = next();
        for (int bit = 7; bit >= 0 && out.size() < size; --bit) {
            if (flags & (1 << bit)) out.push_back(next());
            else {
                unsigned first = next(), second = next(), distance = ((first&15) << 8) + second + 1;
                unsigned length = first >> 4; length = length ? length + 2 : next() + 18;
                if (distance > out.size()) throw std::runtime_error("Invalid Yaz0 back reference");
                for (unsigned i = 0; i < length && out.size() < size; ++i) out.push_back(out[out.size()-distance]);
            }
        }
    }
    return out;
}
Asset yaz0_literals(const Bytes& bytes) {
    Bytes result(16); memcpy(result.data(), "Yaz0", 4);
    for (unsigned i = 0; i < 4; ++i) result[4+i] = bytes.size() >> (24-8*i);
    for (size_t pos = 0; pos < bytes.size(); pos += 8) {
        result.push_back(0xff);
        result.insert(result.end(), bytes.begin()+pos, bytes.begin()+std::min(pos+8, bytes.size()));
    }
    return Asset::generated(std::move(result));
}
Sha256::Sha256() : state_{0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19} {}
void Sha256::compress() {
    static const uint32_t k[64] = {
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
    uint32_t w[64]; for (unsigned i=0;i<16;++i) w[i]=be32(block_.data()+4*i);
    for (unsigned i=16;i<64;++i) {
        auto s0=ror(w[i-15],7)^ror(w[i-15],18)^(w[i-15]>>3), s1=ror(w[i-2],17)^ror(w[i-2],19)^(w[i-2]>>10);
        w[i]=w[i-16]+s0+w[i-7]+s1;
    }
    auto s=state_;
    for (unsigned i=0;i<64;++i) {
        uint32_t t1=s[7]+(ror(s[4],6)^ror(s[4],11)^ror(s[4],25))+((s[4]&s[5])^(~s[4]&s[6]))+k[i]+w[i];
        uint32_t t2=(ror(s[0],2)^ror(s[0],13)^ror(s[0],22))+((s[0]&s[1])^(s[0]&s[2])^(s[1]&s[2]));
        s={t1+t2,s[0],s[1],s[2],s[3]+t1,s[4],s[5],s[6]};
    }
    for (unsigned i=0;i<8;++i) state_[i]+=s[i];
}
void Sha256::update(const uint8_t* data, size_t size) {
    length_ += size;
    while (size) {
        size_t count=std::min(size, block_.size()-used_);
        std::copy_n(data,count,block_.data()+used_); used_+=count;data+=count;size-=count;
        if (used_==64) {compress();used_=0;}
    }
}
std::array<uint8_t,32> Sha256::finish() {
    uint64_t bits=length_*8;
    block_[used_++]=0x80;
    if (used_>56) {std::fill(block_.begin()+used_,block_.end(),0);compress();used_=0;}
    std::fill(block_.begin()+used_,block_.begin()+56,0);
    for (unsigned i=0;i<8;++i) block_[56+i]=bits>>(56-8*i);
    compress();std::array<uint8_t,32> out{};
    for (unsigned i=0;i<32;++i) out[i]=state_[i/4]>>(24-8*(i%4));
    return out;
}
std::string sha256(const Asset& asset, const Progress& progress) {
    Sha256 hash;
    File source(nullptr,fclose);
    if (!asset.memory) {source=open(asset.path,"rb");seek(source.get(),asset.offset);}
    Bytes buffer(65536);
    for (uint64_t done=0;done<asset.size;) {
        size_t count=std::min<uint64_t>(buffer.size(),asset.size-done);
        if (source) read_exact(source.get(),buffer.data(),count);
        else std::copy_n(asset.memory->data()+asset.offset+done,count,buffer.data());
        hash.update(buffer.data(),count);done+=count;
        if (progress) progress("Checking installed game",done,asset.size);
    }
    std::string hex; const char* digits="0123456789abcdef";
    for (auto byte:hash.finish()) {hex+=digits[byte>>4];hex+=digits[byte&15];}
    return hex;
}
}
