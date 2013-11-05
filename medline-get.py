#!/usr/bin/env python
# encoding: utf-8
import csv 
import sys,re

import datetime
from Bio import Entrez,Medline

import collections
import sqlite3
import os
import urllib2
import sys

conn=sqlite3.connect("local-medline-pdb.db")
cur=conn.cursor()

def medline_create_table(drop=False):
	# Setup the table 
	with conn:
		if drop:
			cur.execute("DROP TABLE IF EXISTS medline")
		cur.execute("CREATE TABLE IF NOT EXISTS medline(pmid int, journal int, receiveddate date, accepteddate date,aheadofprintdate date, publisheddate date, doi int, medentry int,earliestpublicdate date, earliestpublicationdate date, retracted bool, PRIMARY KEY(pmid))")
		# Add indexes 
		for col in ["PMID","doi"]:
			cur.execute("CREATE INDEX IF NOT EXISTS medline_idx_%s ON medline(%s)"%(col,col))

	# conn.commit()
def pdb_create_table(drop=False):
	# Setup the table 
	with conn:
		if drop:
			cur.execute("DROP TABLE IF EXISTS pdb")
		cur.execute("CREATE TABLE IF NOT EXISTS pdb(pdbid text, depodate date,releasedate date,jrnlref int,PRIMARY KEY(pdbid))")
		# Add indexes 
		for col in ["pdbid","jrnlref"]:
			cur.execute("CREATE INDEX IF NOT EXISTS pdb_idx_%s ON pdb(%s)"%(col,col))

medline_create_table()
pdb_create_table()



def medline_store_entry(entry):
	if "PMID" not in entry:
		return
	pmid=int(entry['PMID'])
	if medline_pmids_in_db([pmid])[pmid]: #already stored
		print >>sys.stderr,"Pmid %d already in db"%(pmid)
		return 
	with sqlite3.connect("local-medline-pdb.db") as conn:
		cur=conn.cursor()
		pmid=int(entry['PMID'])
		if "TA" in entry:
			journal=entry['TA']
		elif "JT" in entry:
			journal=entry['JT']
		if "PHST" not in entry:
			print >> sys.stderr,"No PHST info for pmid",pmid
			receiveddate=None
			accepteddate=None
			aheaddate=None
		# We parse the PHST field 
		else:

			try:
				receiveddate=[x for x in entry['PHST'] if x.endswith("[received]")]
				receiveddate=datetime.datetime.strptime(receiveddate[0].split(" ")[0],"%Y/%m/%d")
			except (ValueError,IndexError):
				receiveddate=None

			try:
				accepteddate=[x for x in entry['PHST'] if x.endswith("[accepted]")]
				accepteddate=datetime.datetime.strptime(accepteddate[0].split(" ")[0],"%Y/%m/%d")
			except (ValueError,IndexError):
				accepteddate=None

			try:
				aheaddate=[x for x in entry['PHST'] if x.endswith("[aheadofprint]")]
				aheaddate=datetime.datetime.strptime(aheaddate[0].split(" ")[0],"%Y/%m/%d")
			except (ValueError,IndexError):
				aheaddate=None

		if "DP" in entry: #Published date
			publisheddate=entry['DP']
			try:
				if "-" in publisheddate:
					print >> sys.stderr,"Wrong format for DP of pmid",pmid,publisheddate
					publisheddate=None
				elif len(publisheddate.split())==3:
					publisheddate=datetime.datetime.strptime(publisheddate,"%Y %b %d")
				elif len(publisheddate.split())==2: #Sometimes only month and year are given
					publisheddate=datetime.datetime.strptime(publisheddate,"%Y %b")
			except ValueError:
					print >> sys.stderr,"Cannot parse publisheddate",publisheddate
					publisheddate=None
		else:
			publisheddate=None

		# Parse the doi, fallback to pii if NA 
		if "AID" in entry:
			doi=[x for x in entry['AID'] if x.endswith("[doi]")]
			if len(doi)==0:
				doi=[x for x in entry['AID'] if x.endswith("[pii]")]
			if len(doi)==0:
				doi==""
			else:
				doi=doi[0].split(" ")[0]
		else:
			doi=""
		print pmid,journal,receiveddate,accepteddate,aheaddate,publisheddate,doi
		cur.execute("INSERT INTO medline (pmid,journal,receiveddate,accepteddate,aheadofprintdate,publisheddate,doi,medentry) VALUES (?,?,?,?,?,?,?,?)",\
			(pmid,journal,receiveddate,accepteddate,aheaddate,publisheddate,doi,repr(entry)))


def medline_pmids_in_db(pmids):
	cur=conn.cursor()
	cur.execute("SELECT pmid FROM medline")
	allpmids=set([x[0] for x in cur.fetchall()])
	assoc_table={}
	for p in pmids:
		assoc_table[p]=p in allpmids
	return assoc_table

def medline_download_entries(pmids):
	Entrez.email="massyah@gmail.com"
	request = Entrez.epost("pubmed",id=",".join(map(str,pmids)))
	result = Entrez.read(request)
	webEnv = result["WebEnv"]
	queryKey = result["QueryKey"]
	handle = Entrez.efetch(db="pubmed",rettype="medline",retmode="text", webenv=webEnv, query_key=queryKey)
	all_entries=[]
	for r in Medline.parse(handle):
		all_entries.append(r)
	return all_entries



def pdb_id_in_db(pdbids):
	cur=conn.cursor()
	cur.execute("SELECT pdbid FROM pdb")
	all_pdb_id=set([x[0] for x in cur.fetchall()])
	assoc_table={}
	for p in pdbids:
		assoc_table[p]=p in all_pdb_id
	return assoc_table


def pdb_store_entry(pdbid):
	# Already in the db?
	if pdb_id_in_db([pdbid])[pdbid]:
		print >>sys.stderr,"PDB entry %s already in the db"%(pdbid)
		return 

	# We wget it if it doesn't exists
	available_entries=set([x.split(".")[0] for x in os.listdir("pdb-entries/")])
	if pdbid not in available_entries:
		entry=pdb_download_entry(pdbid)
		fields=pdb_parse_entry(entry)
		if not entry:
			print >> sys.stderr,"Cannot get entry %s from PDB"%(pdbid)
			return 
	else:
		with open("pdb-entries/%s.pdb.txt"%(pdbid),"r") as f:
			fields=pdb_parse_entry(f.read())
	print fields

	cur=conn.cursor()
	values=(fields['pdbid'],fields['depodate'],fields['releasedate'],fields['jrnlref'])
	cur.execute("INSERT INTO pdb(pdbid,depodate,releasedate,jrnlref) VALUES(?,?,?,?)",values)

def pdb_store_entries_not_in_db():
	conn=sqlite3.connect("local-medline-pdb.db")
	cur=conn.cursor()
	available_entries=set([x.split(".")[0] for x in os.listdir("pdb-entries/") if (os.path.isfile("pdb-entries/"+x) and not x.startswith("."))])
	cur.execute("SELECT pdbid FROM pdb")
	pdb_in_db=[x[0] for x in cur.fetchall()]
	to_insert=set(available_entries).difference(pdb_in_db)
	print len(to_insert)
	for ent in to_insert:
		pdb_store_entry(ent)
	conn.commit()


def get_medlines_for_pdbs():
	cur=conn.cursor()
	cur.execute("SELECT jrnlref FROM pdb")
	pdb_pmids=[x[0] for x in cur]
	pdb_pmids=medline_pmids_in_db(pdb_pmids)
	missing_pmids=[x for x in pdb_pmids if not pdb_pmids[x]]
	print >> sys.stderr,"Will download",len(missing_pmids),"pmids"
	# Batch of 500 
	for i in range(0,len(missing_pmids),500):
		to_get=[x for x in missing_pmids[i:i+500] if x] #filter the None
		entries=medline_download_entries(to_get)

		for e in entries:medline_store_entry(e)
	conn.commit()


def get_medlines_for_gse():
	connGSE=sqlite3.connect("GEOmetadb.sqlite")
	curGSE=connGSE.cursor()
	curGSE.execute("SELECT pubmed_id FROM gse")
	gse_pmids=[x[0] for x in curGSE]
	gse_pmids=medline_pmids_in_db(gse_pmids)
	missing_pmids=[x for x in gse_pmids if not gse_pmids[x]]
	print >> sys.stderr,"Will download",len(missing_pmids),"pmids"

	# Batch of 500 
	for i in range(0,len(missing_pmids),500):
		to_get=[x for x in missing_pmids[i:i+500] if x] #filter the None
		entries=medline_download_entries(to_get)

		for e in entries:medline_store_entry(e)
	conn.commit()
	correct_ahead_of_print()
	add_earliest_public_date()
	add_earliest_publication_date()
	update_retractations()



def pdb_parse_citation_entries():
	processed_lines=0
	with open("pdb-all-citations-report-20121009.csv","r") as csvfile:
		pdb_reader=csv.reader(csvfile)
		pdb_reader.next()
		try:
			for row in pdb_reader:
				processed_lines+=1
				pdbid=row[0]
				jrnlref=row[-1]
				if jrnlref=="-1":
					continue
				pdb_store_entry(pdbid)
				if (processed_lines%100)==0:
					print "*"*12,processed_lines
					sys.stdout.flush()
		except:
			print "Unexpected error:", sys.exc_info()[0]
			conn.commit()
			raise


def correct_ahead_of_print():
	cur.execute("SELECT pmid,aheadofprintdate,publisheddate,medentry FROM medline WHERE aheadofprintdate IS NULL")

	ahed=dict()
	published=dict()
	for r in cur:
		e=eval(r[-1])
		pmid=r[0]
		if "PHST" not in e:
			continue
		try:
			aheaddate=[x for x in e['PHST'] if x.endswith("[aheadofprint]")]
			aheaddate=datetime.datetime.strptime(aheaddate[0].split(" ")[0],"%Y/%m/%d")
		except (ValueError,IndexError):
			aheaddate=None
		if aheaddate:
			ahed[pmid]=aheaddate
	print len(ahed),"will be corrected"
	values=[(x[1],x[0]) for x in ahed.items()]
	sql='UPDATE medline SET aheadofprintdate=? WHERE pmid=?'
	cur.executemany(sql,values)




def fallback_date_parser(date_string,verbose=False):
	formats=[
	"%Y/%m/%d %H:%M",
	"%Y/%m/%d",
	"%Y%m%d",
	"%Y %b %d",
	"%Y/%m",
	"%Y %m",
	"%Y %b"
	]
	for f in formats:
		try:
			parsed=datetime.datetime.strptime(date_string,f)
			if verbose:
				print "->",parsed
			return parsed
		except Exception as e: 
			continue
	if verbose:
		print "unable to parse date",date_string
	return None

def get_all_dates_for_pmid(pmid):
	conn=sqlite3.connect("local-medline-pdb.db")
	cur=conn.cursor()
	cur.execute("SELECT pmid,medentry FROM medline WHERE pmid=?",(pmid,))

	entry=cur.fetchone()

	return get_all_dates(eval(entry[1]))

def get_all_dates(entry,verbose=False):
	"""Return a dict mapping with all the dates found in the MEDLINE entry
	based on the formats from http://www.nlm.nih.gov/bsd/mms/medlineelements.html#dp
	"""
	all_dates=dict()
	if "PHST" in entry:
		if verbose:
			print "phst",entry["PHST"]
	
		receiveddate=accepteddate=revised=aheadofprint=None
		for e in entry["PHST"]:
			date,dtype=e.split(" ")
			if dtype=="[received]":
				all_dates['receiveddate']=fallback_date_parser(date)
			elif dtype=="[accepted]":
				all_dates['accepteddate']=fallback_date_parser(date)
			elif dtype=="[revised]":
				all_dates['reviseddate']=fallback_date_parser(date)
			elif dtype=="[aheadofprint]":
				all_dates['aheadofprintdate']=fallback_date_parser(date)

	if "DP" in entry: #Published date
		if verbose:
			print "dp",entry['DP']
		publisheddate=entry['DP']
		publisheddate=fallback_date_parser(publisheddate)
		all_dates['publisheddate']=publisheddate

	if "DA" in entry: #Date added to medline
		if verbose:
			print "da",entry['DA']
		date_added=fallback_date_parser(entry['DA'])
		all_dates['dateadded']=date_added
	if "PMCR" in entry: #PMC embargo date
		if verbose:
			print "pmcr",entry['PMCR']
		date_added=fallback_date_parser(entry['PMCR'])
		all_dates['pmcembargo']=date_added
	# Maybe parse the SO field?
	if "DEP" in entry:
		if verbose:
			print "dep",entry['DEP']
		date_added=fallback_date_parser(entry['DEP'])
		all_dates['dep']=date_added
	if "EDAT" in entry:
		if verbose:
			print "edat",entry['EDAT']
		date_added=fallback_date_parser(entry['EDAT'])
		all_dates['edat']=date_added

	# if "MHDA" in entry: # date at which mesh were added
	# 	if verbose:
	# 		print "mhda",entry['MHDA']
	# 	date_added=fallback_date_parser(entry['MHDA'])
	# 	all_dates['mhda']=date_added

	return all_dates

def add_earliest_public_date():
	conn=sqlite3.connect("local-medline-pdb.db")
	cur=conn.cursor()
	cur.execute("SELECT pmid,medentry FROM medline")
	to_update=dict()
	for r in cur:
		e=eval(r[-1])
		all_dates=get_all_dates(e)
		min_date=min([x for x in all_dates.values() if x])
		to_update[r[0]]=min_date
	values=[(x[1],x[0]) for x in to_update.items()]
	sql='UPDATE medline SET earliestpublicdate=? WHERE pmid=?'
	cur.executemany(sql,values)
	conn.commit()


def add_earliest_publication_date():
	conn=sqlite3.connect("local-medline-pdb.db")
	cur=conn.cursor()
	cur.execute("SELECT pmid,medentry FROM medline")
	to_update=dict()
	res=cur.fetchall()
	print len(res),"entries to update"
	for r in res:
		e=eval(r[-1])
		all_dates=get_all_dates(e)
		min_pub_date=min([v for k,v in all_dates.items() if ((k in ['publisheddate','edat','dateadded','aheadofprint','aheadofprintdate','dep','accepteddate']) and v!=None) ])
		to_update[r[0]]=min_pub_date
		if (len(to_update) % 100) == 0:
			print len(to_update),"entries parsed"
	print "Will update DB"
	values=[(x[1],x[0]) for x in to_update.items()]
	sql='UPDATE medline SET earliestpublicationdate=? WHERE pmid=?'
	cur.executemany(sql,values)
	print "Will commit"
	conn.commit()

def add_latest_public_date():
	conn=sqlite3.connect("local-medline-pdb.db")
	cur=conn.cursor()
	cur.execute("SELECT pmid,earliestpublicdate,latestpublicdate,medentry FROM medline")
	to_update=dict()
	for r in cur:
		e=eval(r[-1])
		latestpublicdate=r[2]
		all_dates=get_all_dates(e)
		max_date=max([x for x in all_dates.values() if x])
		to_update[r[0]]=max_date
		print latestpublicdate,max_date
	values=[(x[1],x[0]) for x in to_update.items()]
	sql='UPDATE medline SET latestpublicdate=? WHERE pmid=?'
	cur.executemany(sql,values)
	conn.commit()


def update_retractations():
	conn=sqlite3.connect("local-medline-pdb.db")
	cur=conn.cursor()
	cur.execute("SELECT pmid,medentry FROM medline")
	to_update=dict()
	all_pts=collections.defaultdict(int)
	retract=0
	for r in cur:
		e=eval(r[-1])
		for pt in e['PT']:
			all_pts[pt]+=1
			if "retract" in pt.lower():
				to_update[r[0]]=True
			else:
				to_update[r[0]]=False
		if to_update[r[0]]:
			retract+=1
			print r[0]
	return retract,all_pts
	# values=[(x[1],x[0]) for x in to_update.items()]
	# sql='UPDATE medline SET retracted=? WHERE pmid=?'
	# cur.executemany(sql,values)
	# conn.commit()


def print_all_dates_for_pmid(pmid):
	conn=sqlite3.connect("local-medline-pdb.db")
	cur=conn.cursor()

	cur.execute("SELECT medentry FROM medline WHERE pmid=?",(pmid,))
	dates=get_all_dates(eval(cur.fetchone()[0]))
	for k,v in dates.items():
		print k,v