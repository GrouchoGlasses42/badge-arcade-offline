#include "nba.hpp"
#include <iostream>

int main(int argc,char** argv) {
    try {
        if(argc<3) throw std::runtime_error("Usage: nba-host hash FILE | week SARC | build BASE UPDATE SCHEDULE OUTPUT [WEEK_SARC] [--synthetic]");
        std::string command=argv[1];
        if(command=="hash") std::cout<<nba::sha256(nba::Asset::file(argv[2]))<<'\n';
        else if(command=="sarc" && argc==4) nba::write_sarc(nba::read_sarc(nba::Asset::file(argv[2])),argv[3]);
        else if(command=="yaz0" && argc==4) nba::write_file(argv[3],nba::yaz0(nba::Asset::file(argv[2])));
        else if(command=="week") {
            auto week=nba::read_week(nba::Asset::file(argv[2]));
            std::cout<<week.start<<' '<<week.stages.size()<<'\n';
        } else if(command=="build") {
            if(argc<6) throw std::runtime_error("Build requires BASE UPDATE SCHEDULE OUTPUT");
            nba::Build request;request.base_archive=argv[2];request.update_archive=argv[3];request.schedule=argv[4];
            for(int i=6;i<argc;++i) {
                if(std::string(argv[i])=="--synthetic") request.verify_inputs=false;
                else if(std::string(argv[i])=="--allbadge" && i+1<argc) request.allbadge=std::make_shared<nba::Asset>(nba::read_allbadge(nba::Asset::file(argv[++i])));
                else request.week=std::make_shared<nba::Week>(nba::read_week(nba::Asset::file(argv[i])));
            }
            auto catalog=nba::build_content(request,argv[5]);
            std::cout<<catalog.machines<<' '<<catalog.prizes<<' '<<catalog.selection<<'\n';
        }
        else throw std::runtime_error("Unknown host check command");
        return 0;
    } catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
