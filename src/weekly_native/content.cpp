#include "nba.hpp"
#include "tinyxml2.h"
#include "picojson.h"
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <set>

namespace nba {
namespace {
struct Registry { const char *block, *tag, *prefix, *suffix; unsigned capacity; };
const Registry registries[]={
    {"Categories","Category","pc/rt/Ca/",".cab.szs",200},
    {"Cranes","Crane","pc/rt/Cr/",".crb.szs",1500},
    {"CraneIcons","CraneIcon","pc/rt/CI/",".icb.szs",2000},
    {"Prizes","Prize","pc/rt/Pr/",".prb.szs",10000},
    {"Attachments","Attachment","pc/rt/At/",".atb.szs",200},
    {"FixedObjects","FixedObject","pc/rt/FO/",".fob.szs",500},
    {"CraneInstances","CraneInstance","pc/ci/",".cib.szs",2000}
};
bool starts(const std::string& value,const std::string& prefix) {return value.compare(0,prefix.size(),prefix)==0;}
bool ends(const std::string& value,const std::string& suffix) {
    return value.size()>=suffix.size() && value.compare(value.size()-suffix.size(),suffix.size(),suffix)==0;
}
const Asset& need(const Files& files,const std::string& name) {
    auto i=files.find(name);if(i==files.end()) throw std::runtime_error("Missing machine resource: "+name);return i->second;
}
void parse(tinyxml2::XMLDocument& doc,const Asset& asset) {
    auto bytes=asset.read();
    if(doc.Parse(reinterpret_cast<const char*>(bytes.data()),bytes.size())!=tinyxml2::XML_SUCCESS)
        throw std::runtime_error("Invalid game XML");
}
std::string xml_text(tinyxml2::XMLElement* node,const char* name) {
    auto* child=node->FirstChildElement(name);return child&&child->GetText()?child->GetText():"";
}
Asset serialize(tinyxml2::XMLDocument& doc) {
    tinyxml2::XMLPrinter printer(nullptr,true);doc.Print(&printer);return Asset::text(printer.CStr());
}
void set_text(tinyxml2::XMLDocument& doc,tinyxml2::XMLElement* parent,const char* tag,const std::string& value) {
    auto* node=parent->FirstChildElement(tag);if(!node) {node=doc.NewElement(tag);parent->InsertEndChild(node);}node->SetText(value.c_str());
}
void name_at(Bytes& raw,size_t offset,const std::string& name) {
    if(name.size()>47 || offset+48>raw.size()) throw std::runtime_error("Invalid generated machine name");
    std::fill_n(raw.begin()+offset,48,0);std::copy(name.begin(),name.end(),raw.begin()+offset);
}
std::vector<std::string> dependencies(const Bytes& raw) {
    std::vector<std::string> result={"pc/rt/Cr/"+resource_name(raw,0x60)+".crb.szs", "pc/rt/CI/"+resource_name(raw,0x90)+".icb.szs"};
    const size_t bases[]={0x1100,0x14c0,0x1880};
    for(unsigned kind=0;kind<3;++kind) {
        // Nintendo's allbadge catalog omits playfield attachments/obstacles.
        // Display-only layouts need badge artwork but never instantiate them.
        if(kind && le32(raw,0xc0)==1) continue;
        unsigned count=le32(raw,0xe0+kind*4);if(count>20) throw std::runtime_error("Oversized machine dependency table");
        for(unsigned i=0;i<count;++i) result.emplace_back(std::string(registries[kind+3].prefix)+resource_name(raw,bases[kind]+48*i)+registries[kind+3].suffix);
    }
    return result;
}
void bonus_catchers(Files& files) {
    std::set<std::string> referenced;std::set<uint32_t> ids;
    for(const auto& file:files) if(ends(file.first,".cib.szs")) {
        auto raw=yaz0(file.second);ids.insert(le32(raw,0x2c));
        if(le32(raw,0xc0)==0) for(unsigned i=0;i<le32(raw,0xe0);++i) {
            if(i>=20) throw std::runtime_error("Oversized prize table");
            referenced.insert(resource_name(raw,0x1100+48*i));
        }
    }
    std::vector<std::string> unassigned;
    for(const auto& file:files) if(starts(file.first,"pc/rt/Pr/")&&ends(file.first,".prb.szs")) {
        auto name=file.first.substr(9,file.first.size()-9-8);
        if(!referenced.count(name)) unassigned.push_back(name);
    }
    if(unassigned.empty()) return;
    if(unassigned.size()%4) throw std::runtime_error("Bundled bonus badges do not fill four-badge machines");
    auto base=yaz0(need(files,"pc/ci/Kirby_001.cib.szs"));
    const uint32_t expected[]={4,0,1,4,4,0,1,0};
    for(unsigned i=0;i<8;++i) if(le32(base,0xe0+i*4)!=expected[i]) throw std::runtime_error("Unexpected bonus machine template");
    auto icon_base=yaz0(need(files,"pc/rt/CI/"+resource_name(base,0x90)+".icb.szs"));
    for(unsigned group=0;group<unassigned.size()/4;++group) {
        char suffix[16];snprintf(suffix,sizeof(suffix),"%03u",group+4);
        std::string name="BTCenter_"+std::string(suffix),icon_name="CraneIcon_"+name;
        if(files.count("pc/ci/"+name+".cib.szs") || ids.count(4600+group)) throw std::runtime_error("Bonus catcher identity collision");
        auto raw=base;put32(raw,0x2c,4600+group);name_at(raw,0x30,name);name_at(raw,0x90,icon_name);
        std::string title="Arcade Bunny Bonus "+std::to_string(group+1);
        if(raw.size()<0x1100) throw std::runtime_error("Truncated machine title table");
        std::fill(raw.begin()+0x100,raw.begin()+0x1100,0);
        for(unsigned language=0;language<16;++language)
            for(unsigned i=0;i<title.size();++i) raw[0x100+language*256+i*2]=title[i];
        for(unsigned i=0;i<4;++i) {
            const auto& prize=unassigned[group*4+i];auto badge=yaz0(need(files,"pc/rt/Pr/"+prize+".prb.szs"),0xa4);
            if(resource_name(badge,0x74)!="BTCenter") throw std::runtime_error("Unexpected unassigned badge category");
            name_at(raw,0x1100+48*i,prize);
        }
        auto icon=icon_base;name_at(icon,0x1c,icon_name);
        auto first=yaz0(need(files,"pc/rt/Pr/"+unassigned[group*4]+".prb.szs"));
        if(first.size()<0x3100 || icon.size()<0x2100) throw std::runtime_error("Truncated badge icon texture");
        std::copy(first.begin()+0x1100,first.begin()+0x3100,icon.begin()+0x100);
        files["pc/ci/"+name+".cib.szs"]=yaz0_literals(raw);
        files["pc/rt/CI/"+icon_name+".icb.szs"]=yaz0_literals(icon);
    }
}
}
Catalog build_content(const Build& request,const std::string& output,const Progress& progress) {
    auto base_asset=Asset::file(request.base_archive),update_asset=Asset::file(request.update_archive),schedule_asset=Asset::file(request.schedule);
    if(request.verify_inputs) {
        const std::pair<Asset,const char*> inputs[]={
            {base_asset,"2aca8529d7981a9ccad5a448ea06996fc861190b570ee4b25e4c651ce26347a5"},
            {update_asset,"0f379f61166ced829c0f757ade31c00c09ed8e849350edaa8fec2a30974dae48"},
            {schedule_asset,"af0f27304a495c3d8fd202631702016bffe0874471962f12cc45a297cb8887ab"}
        };
        for(const auto& input:inputs) if(sha256(input.first,progress)!=input.second)
            throw std::runtime_error("Installed content does not match supported EUR base 1.3.0 / update 1.3.1");
    }
    Files files=read_sarc(base_asset);
    for(const auto& entry:read_sarc(update_asset)) files[entry.first]=entry.second;
    std::set<std::string> chosen;
    std::string bonus;
    if(request.week) {
        if(!request.allbadge) throw std::runtime_error("Weekly patches require the full allbadge_v131 catalog");
        std::set<std::string> collection;
        for(const auto& entry:read_sarc(read_allbadge(*request.allbadge))) {
            if(starts(entry.first,"pc/rt/")||starts(entry.first,"pc/ci/")) files[entry.first]=entry.second;
            if(ends(entry.first,".cib.szs")) collection.insert(entry.first);
        }
        for(const auto& entry:read_sarc(request.week->archive))
            if(starts(entry.first,"pc/rt/")||starts(entry.first,"pc/ci/")) files[entry.first]=entry.second;
        // A single name is one machine even if it appears on several days or
        // as both a normal and bonus machine. No calendar filtering survives.
        for(const auto& stage:request.week->stages) {
            chosen.insert(stage.name);
            if(bonus.empty() && stage.key=="BonusStageName") bonus=stage.name;
        }
        if(chosen.empty() || chosen.size()>512) throw std::runtime_error("Week has too many unique machines");
        // Full catalog layouts remain in the collection viewer. Only this
        // week's union is playable; other allbadge layouts are display-only.
        std::set<std::string> needed=collection;
        for(const auto& name:chosen) {
            auto path="pc/ci/"+name+".cib.szs";need(files,path);needed.insert(path);
        }
        for(const auto& file:files) if(ends(file.first,".cib.szs") && le32(yaz0(file.second,0xc4),0xc0)==2) needed.insert(file.first);
        auto layouts=needed;
        for(const auto& path:layouts) {
            auto raw=yaz0(need(files,path));
            auto name=path.substr(6,path.size()-6-8);
            if(collection.count(path) && !chosen.count(name) && le32(raw,0xc0)!=2) {
                put32(raw,0xc0,1);files[path]=yaz0_literals(raw);
            }
            if(chosen.count(name) && le32(raw,0xc0)!=0) throw std::runtime_error("Archived lineup references a display-only machine");
            for(const auto& dependency:dependencies(raw)) {need(files,dependency);needed.insert(dependency);}
        }
        for(auto it=files.begin();it!=files.end();) {
            bool prune=ends(it->first,".cib.szs") || starts(it->first,"pc/rt/Cr/") || starts(it->first,"pc/rt/CI/");
            if(prune && !needed.count(it->first)) it=files.erase(it);else ++it;
        }
    } else bonus_catchers(files);
    tinyxml2::XMLDocument registry;parse(registry,need(files,"pc/PrizeCollection.xml"));
    auto* registry_root=registry.RootElement();if(!registry_root) throw std::runtime_error("Missing catalog registry root");
    std::map<std::string,std::vector<std::string>> names;
    for(const auto& kind:registries) {
        auto* node=registry_root->FirstChildElement(kind.block);
        if(!node) throw std::runtime_error("Missing resource registry");
        auto& list=names[kind.block];
        for(const auto& entry:files) if(starts(entry.first,kind.prefix)&&ends(entry.first,kind.suffix))
            list.push_back(entry.first.substr(strlen(kind.prefix),entry.first.size()-strlen(kind.prefix)-strlen(kind.suffix)));
        if(list.empty() || list.size()>kind.capacity) throw std::runtime_error(std::string(kind.block)+" exceeds verified native capacity");
        node->DeleteChildren();node->SetAttribute("count",static_cast<unsigned>(list.size()));
        for(const auto& name:list) {auto* item=registry.NewElement(kind.tag);item->SetAttribute("name",name.c_str());node->InsertEndChild(item);}
    }
    std::map<std::string,uint32_t> categories;std::set<uint32_t> category_ids;
    for(const auto& name:names["Categories"]) {
        uint32_t id=le32(yaz0(need(files,"pc/rt/Ca/"+name+".cab.szs"),0x68),0x24);
        if(!category_ids.insert(id).second) throw std::runtime_error("Duplicate category identity");
        categories[name]=id;
    }
    std::set<std::pair<uint32_t,uint32_t>> prizes;
    for(const auto& name:names["Prizes"]) {
        auto raw=yaz0(need(files,"pc/rt/Pr/"+name+".prb.szs"),0xa4);auto category=categories.find(resource_name(raw,0x74));
        if(category==categories.end() || !prizes.emplace(category->second,le32(raw,0x3c)).second)
            throw std::runtime_error("Missing category or duplicate badge identity");
    }
    std::vector<std::string> normal;std::set<std::string> reachable;
    for(const auto& name:names["CraneInstances"]) {
        auto raw=yaz0(need(files,"pc/ci/"+name+".cib.szs"));
        for(const auto& dependency:dependencies(raw)) need(files,dependency);
        if(le32(raw,0xc0)==0) {
            normal.push_back(name);
            for(unsigned i=0;i<le32(raw,0xe0);++i) reachable.insert(resource_name(raw,0x1100+48*i));
        }
    }
    if(normal.empty() || normal.size()>512) throw std::runtime_error("Unsupported normal machine count");
    if(request.week && std::set<std::string>(normal.begin(),normal.end())!=chosen)
        throw std::runtime_error("Weekly catalog contains an unintended machine");
    if(!request.week && reachable!=std::set<std::string>(names["Prizes"].begin(),names["Prizes"].end()))
        throw std::runtime_error("Default lineup does not cover all bundled badges");
    files["pc/PrizeCollection.xml"]=serialize(registry);
    tinyxml2::XMLDocument schedule;parse(schedule,schedule_asset);
    auto* root=schedule.FirstChildElement("FileItems");auto* items=root?root->FirstChildElement("Items"):nullptr;
    if(!items) throw std::runtime_error("Missing native schedule Items");
    for(auto* item=items->FirstChildElement();item;) {
        auto* next=item->NextSiblingElement();auto key=xml_text(item,"Key");
        if(starts(key,"DefaultStageName")||key=="BonusStageName"||xml_text(item,"RegexSetName")=="PrizeCollection") items->DeleteChild(item);
        else {set_text(schedule,item,"DateStartText","20000101");set_text(schedule,item,"DateExpireText","20991231");}
        item=next;
    }
    auto add=[&](const std::string& key,const std::string& name,const char* kind,unsigned priority) {
        auto* item=schedule.NewElement("FileItem");items->InsertEndChild(item);
        set_text(schedule,item,"Priority",std::to_string(priority));set_text(schedule,item,"DateStartText","20000101");
        set_text(schedule,item,"DateExpireText","20991231");set_text(schedule,item,"RegexSetName",kind);
        set_text(schedule,item,"Key",key);set_text(schedule,item,"Value",name);
    };
    for(unsigned i=0;i<normal.size();++i) {
        char key[32];snprintf(key,sizeof(key),"DefaultStageName%03u",i);add(key,normal[i],"DefaultStage",100+i);
    }
    if(!bonus.empty()) add("BonusStageName",bonus,"BonusStage",1000);
    unsigned count=0;for(auto* item=items->FirstChildElement();item;item=item->NextSiblingElement()) ++count;
    set_text(schedule,root,"ItemsCount",std::to_string(count));
    auto timetable=serialize(schedule);
    mkdirs(output+"/romfs/region_common");mkdirs(output+"/romfs/region_EUR/common/sharc");
    copy_file(timetable,output+"/romfs/region_common/Schedule.xml");
    copy_file(timetable,output+"/romfs/region_EUR/common/Schedule.xml");
    write_sarc(files,output+"/romfs/region_EUR/common/sharc/pc.sarc",progress);
    Catalog result{static_cast<unsigned>(prizes.size()),static_cast<unsigned>(normal.size()),request.week?request.week->start:"default"};
    picojson::object manifest;
    manifest["schema"]=picojson::value(1.0);manifest["mode"]=picojson::value(std::string(request.week?"week":"default"));
    manifest["week"]=picojson::value(result.selection);manifest["home_menu"]=picojson::value(request.home);
    manifest["machines"]=picojson::value(double(result.machines));manifest["badge_resources"]=picojson::value(double(result.prizes));
    manifest["unique_weekly_machines"]=picojson::value(bool(request.week));
    manifest["full_allbadge_catalog"]=picojson::value(bool(request.allbadge));
    copy_file(Asset::text(picojson::value(manifest).serialize()+"\n"),output+"/catalog.json");
    return result;
}
}
