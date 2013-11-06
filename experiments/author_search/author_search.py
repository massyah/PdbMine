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

# Manual check here! 

## Manual selection for variations present in the index
variants={}
# variants['Perrakis']=["Perrakis, A", "Perrakis A", "Perrakis, Anastassis"]
# variants['Kleywegt']= ["Kleywegt GJ", "Kleywegt, G J", "Kleywegt, Gerard J"]
# variants['gilliland']=["Gilliland GL", "Gilliland G", "Gilliland, Gary", "Gilliland, Gary L", "Gilliland, G L"]
# variants['McPherson']=["McPherson, Alexander", "McPherson, A", "McPherson, Andrew", "McPherson A"]
# variants["read"]=["Read J", "Read, R J", "Read, Randy J", "Read RJ"]
# variants['adams']=["Adams, Paul", "Adams, Paul D", "Adams PD", "Adams, Peter D"]
# variants["macKinnon"]=["MacKinnon R", "Mackinnon R", "MacKinnon, R", "Mackinnon, Roderick", "Mackinnon, R", "MacKinnon, Roderick"]
# variants["Kornberg"]=["Kornberg, R D","Kornberg, Roger D","Kornberg RD"]
# variants["Ramakrishnan"]=["Ramakrishnan, V","Ramakrishnan, Venki"]
# variants["Steintz"]=["Steitz, Thomas A","Steitz, T A","Steitz TA"]
# variants["yonath"]=["Yonath A","Yonath, A","Yonath, Ada"]
variants["kobilka"]=["Kobilka BK","Kobilka, Brian K",]

print "Authors variant to n entries:"
for k,v in variants.items():
	for variant in v:
		print k,variant,len(authors_to_pmid.get(variant,[]))


# Generate the CSV files with the PMIDs 


with open('author_search.csv', 'wa') as csvfile:
	pdbwriter = csv.writer(csvfile, delimiter=',',quoting=csv.QUOTE_MINIMAL)
	for k,v in variants.items():
		for variant in v:
			print k,variant,len(authors_to_pmid.get(variant,[]))
			for pmid in authors_to_pmid.get(variant,[]):
			    pdbwriter.writerow((k,variant, pmid))

print "output written to author_search.csv"