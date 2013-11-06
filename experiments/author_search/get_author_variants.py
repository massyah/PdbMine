#!/usr/bin/env python
# encoding: utf-8
import csv 
import sys,re
import cPickle
import datetime
#from Bio import Entrez,Medline

import collections
import sqlite3
import os
import urllib2
import sys

conn=sqlite3.connect("../../local-medline-pdb_SUBMITTED.db")
cur=conn.cursor()


#author_index=
authors_to_pmid=cPickle.load(open("author_index.cpickle.bdat","r"))


# read author list, take query as the key 
author_list = dict([x.strip().split("\t") for x in open("author_list.tsv")])
 
# Grep authors to get potential variants from the db 

print "Possible other variants: "

re_words = re.compile("\W+")
for a_query,known_variants in author_list.items():
	a_query=a_query.lower()
	other_variants=[x for x in authors_to_pmid.keys() if a_query in re_words.split(x.lower()) and (x not in known_variants)]
	print a_query,"\t",repr(other_variants)
