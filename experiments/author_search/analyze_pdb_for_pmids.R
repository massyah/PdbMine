# library(lattice)
# library(xtable)
# library(scales)

# library(RSQLite)
# library(RUnit)
# library(gdata)
# library(gridExtra)
# library(RColorBrewer)
# library(rentrez)
# library(reshape2)
# library(lubridate)

library(ggplot2)

library(data.table)
# setwd("~/temp/PdbMine/")

load("../../data/pdb.medline.RData")
pdb_medline<-data.table(pdb.medline)
pdb_medline$pmid<-as.integer(as.character(pdb_medline$pmid))
pmid_selection <- fread("author_search.csv")
setnames(pmid_selection,c("V1","V2","V3"),c("key","author","pmid"))

pmid_selection<-merge(pmid_selection,pdb_medline,by="pmid")

# Perform the callings 

ggplot(pmid_selection,aes(x=pubyear,fill=key))+geom_bar()

write.table(pmid_selection,file="author_search_with_pdb_data.tsv",quote=FALSE,row.names=F,sep="\t")
print("output written to author_search_with_pdb_data.tsv")

# pmid_selection[,.N,by=list(pubyear,key,time)][time!='On time']

# pmid_selection[grep("Perrakis",author)][time=="Late"]