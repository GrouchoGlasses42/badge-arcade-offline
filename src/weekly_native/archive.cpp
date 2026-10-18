#include "nba.hpp"
#include "tinyxml2.h"
#include <algorithm>
#include <set>

namespace nba {
namespace {
std::string text(const tinyxml2::XMLElement* node, const char* tag) {
    const auto* child = node->FirstChildElement(tag);
    return child && child->GetText() ? child->GetText() : "";
}
int civil(const std::string& date) {
    std::string digits;
    for (char c : date) if (c != '-') digits += c;
    if (digits.size()!=8 || !std::all_of(digits.begin(),digits.end(),[](char c){return c>='0'&&c<='9';}))
        throw std::runtime_error("Invalid archive date");
    int y=std::stoi(digits.substr(0,4)), m=std::stoi(digits.substr(4,2)), d=std::stoi(digits.substr(6,2));
    if (y<2000 || y>2099 || m<1 || m>12 || d<1) throw std::runtime_error("Unsupported archive date");
    const int month_days[]={31,28,31,30,31,30,31,31,30,31,30,31};
    if (d>month_days[m-1]+(m==2 && y%4==0)) throw std::runtime_error("Invalid archive date");
    int total=0;
    for (int year=2000;year<y;++year) total+=365+(year%4==0);
    for (int month=1;month<m;++month) total+=month_days[month-1]+(month==2 && y%4==0);
    return total+d-1;
}
bool normal_key(const std::string& key) {
    const std::string prefix="DefaultStageName";
    return key.size()==prefix.size()+3 && key.compare(0,prefix.size(),prefix)==0
        && std::all_of(key.end()-3,key.end(),[](char c){return c>='0'&&c<='9';});
}
bool safe_name(const std::string& name) {
    return !name.empty() && name.size()<=47 && std::all_of(name.begin(),name.end(),[](char c){
        return (c>='A'&&c<='Z') || (c>='a'&&c<='z') || (c>='0'&&c<='9') || c=='_';
    });
}
std::string iso(const std::string& date) {
    std::string digits;for(char c:date) if(c!='-') digits+=c;
    civil(digits);return digits.substr(0,4)+"-"+digits.substr(4,2)+"-"+digits.substr(6,2);
}
}
Week read_week(const Asset& archive) {
    auto files=read_sarc(archive);
    auto schedule=files.find("Schedule.xml");
    if(schedule==files.end()) throw std::runtime_error("Pack has no weekly schedule");
    auto xml=schedule->second.read();tinyxml2::XMLDocument doc;
    if(doc.Parse(reinterpret_cast<const char*>(xml.data()),xml.size())!=tinyxml2::XML_SUCCESS)
        throw std::runtime_error("Invalid weekly schedule XML");
    auto* root=doc.FirstChildElement("FileItems");auto* items=root?root->FirstChildElement("Items"):nullptr;
    if(!items) throw std::runtime_error("Weekly schedule has no Items");
    Week out;int start=0,end=0;unsigned packs=0;
    for(auto* item=items->FirstChildElement("FileItem");item;item=item->NextSiblingElement("FileItem")) {
        if(text(item,"RegexSetName")!="PrizeCollection") continue;
        auto found=files.find(text(item,"Value"));
        if(++packs!=1 || found==files.end()) throw std::runtime_error("Missing or ambiguous weekly machine archive");
        out.archive=found->second;out.start=iso(text(item,"DateStartText"));
        start=civil(out.start);end=civil(text(item,"DateExpireText"));
    }
    if(packs!=1 || end-start!=7) throw std::runtime_error("Expected a seven-day archived week");
    bool eur=false,other=false;
    for(const auto& file:files) if(file.first.compare(0,13,"message/boss_")==0) {
        if(file.first.compare(0,17,"message/boss_EUR/")==0) eur=true;else other=true;
    }
    if(other && !eur) throw std::runtime_error("Archived week is not EUR");
    std::array<std::set<std::string>,7> daily;std::set<std::pair<int,std::string>> seen;
    std::array<bool,7> bonus{};
    for(auto* item=items->FirstChildElement("FileItem");item;item=item->NextSiblingElement("FileItem")) {
        auto key=text(item,"Key");if(!normal_key(key) && key!="BonusStageName") continue;
        auto name=text(item,"Value");if(!safe_name(name)) throw std::runtime_error("Invalid archived machine name");
        int first=civil(text(item,"DateStartText"))-start,last=civil(text(item,"DateExpireText"))-start;
        if(first<0 || first>=last || last>7) throw std::runtime_error("Machine dates fall outside week");
        for(int day=first;day<last;++day) {
            if(!seen.emplace(day,key).second) throw std::runtime_error("Overlapping archived slots");
            if(key=="BonusStageName") bonus[day]=true;else daily[day].insert(name);
        }
        out.stages.push_back({key,name,first,last});
    }
    for(unsigned i=0;i<7;++i) if(daily[i].empty() || daily[i].size()>512 || !bonus[i])
        throw std::runtime_error("Each archived day needs normal and bonus machines");
    read_sarc(out.archive);return out;
}
Asset read_allbadge(const Asset& archive) {
    auto files=read_sarc(archive);bool category=false,prize=false,layout=false;
    for(const auto& file:files) {
        category|=file.first.compare(0,9,"pc/rt/Ca/")==0;
        prize|=file.first.compare(0,9,"pc/rt/Pr/")==0;
        layout|=file.first.compare(0,6,"pc/ci/")==0;
    }
    if(!category || !prize || !layout) throw std::runtime_error("Expected the full allbadge resource archive");
    return archive;
}
}
