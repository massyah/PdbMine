import urllib2
import logging
import os.path
import gzip
import datetime
import ftplib
import time
import os
import sqlite3
import sys
import csv
import threading
from Queue import *


CITATIONFILE="pdb-all-citations-report-20121009.csv"
CITATIONFILE="pdb-all-citations-report-20130628.csv"
NMAXTHREADS=20
NMAXTHREADS=6


if "logger" not in globals():

	logger = logging.getLogger('simple_example')
	logger.setLevel(logging.DEBUG)

	# create console handler and set level to debug
	ch = logging.StreamHandler()
	ch.setLevel(logging.DEBUG)

	# create formatter
	formatter = logging.Formatter('%(asctime)s - THR %(thread)d - %(levelname)s - %(message)s')

	# add formatter to ch
	ch.setFormatter(formatter)

	# add ch to logger
	logger.addHandler(ch)


def ftp_download_entries(pdb_ids):
	logger.info("Will get %d entries, from %s to %s",len(pdb_ids),sorted(pdb_ids)[0],sorted(pdb_ids)[-1])
	logger.info("Already present: %d entries",len(set([x.split(".")[0] for x in os.listdir("pdb-entries/")]))
)
	ftp = ftplib.FTP("ftp.wwpdb.org")
	ftp.login("massyah@gmail.com","none")
	ftp.cwd("/pub/pdb/data/structures/all/pdb")
	logger.info("Initiated connection, CWD successful")

	success=0
	tot_entries=len(pdb_ids)
	for entry in pdb_ids:
		file=open("pdb-entries/%s.txt.gz"%(entry),"w")
		ftp.retrbinary("RETR pdb%s.ent.gz"%(entry.lower()),file.write)
		file.close()
		logger.info("Downloaded %s,%d to go",entry,tot_entries-success)
		success+=1
	

	logger.info("%d entries successfully downloaded"%(success))

	return "OK"


def pdb_download_entry(pdbid):
	try:
		entry=urllib2.urlopen('http://www.rcsb.org/pdb/files/%s.pdb?headerOnly=YES'%(pdbid))
		entry_txt=entry.read()
		f=open("pdb-entries/%s.pdb.txt"%(pdbid),"w")
		f.write(entry_txt)
		f.close()
		print "downloaded",pdbid
		# don't harm the PDB server
		time.sleep(0.2)
	except Exception as e:
		print "Could not open document: %s" % pdbid
		print e

class Worker(threading.Thread):
	def __init__(self, function, in_queue, out_queue):
		self.function = function
		self.in_queue, self.out_queue = in_queue, out_queue
		super(Worker, self).__init__()

	def run(self):
		while True:
			try:
				if self.in_queue.empty(): 
					break
				data = self.in_queue.get()
				result = self.function(data)
				self.out_queue.put(result)
				self.in_queue.task_done()
				logger.info("Still %d to do",self.in_queue.qsize())
			except Exception as e:
				logger.critical('something happened!: Error on %s, %s',repr(data),repr(e))
				self.out_queue.put({})
				self.in_queue.task_done()
				break

def process(data, function, num_workers=1):
	in_queue = Queue()
	for item in data:
		in_queue.put(item)
	out_queue = Queue(maxsize=in_queue.qsize())
	workers = [Worker(function, in_queue, out_queue) for i in xrange(num_workers)]
	for worker in workers: 
		worker.setDaemon(True)
		worker.start()
	in_queue.join()
	return out_queue




def parse_citations():
	global all_pdb_ids
	all_pdb_ids=[]
	with open(CITATIONFILE,"r") as csvfile:
		pdb_reader=csv.reader(csvfile)
		pdb_reader.next()
		for row in pdb_reader:
			if row==[]:
				print "error on line",pdb_reader.line_num
				continue
			pdbid=row[0]
			jrnlref=row[-1]
			if jrnlref=="-1":
				continue
			all_pdb_ids.append(pdbid)

if "all_pdb_ids" not in globals():
	parse_citations()



def process_batch_download(nworker=NMAXTHREADS,batch_size=100,maxN=500):
	# Filter out the one already downloaded
	parse_citations()
	available_entries=set([x.split(".")[0] for x in os.listdir("pdb-entries/")])
	pdb_ids_to_get=list(set(all_pdb_ids).difference(available_entries))[0:maxN]
	print "To get",len(pdb_ids_to_get)
	# Take some pdbid to download, split them in lists 

	pdb_ids_to_get=sorted(pdb_ids_to_get)
	batches=[]
	for i in range(0,len(pdb_ids_to_get),batch_size):
		batches.append(pdb_ids_to_get[i:i+batch_size])
	process(batches,ftp_download_entries,nworker)


## Parsing the files in multi-threaded way 

def parse_pdb_entry(pdb_txt):
	pdb_txt=pdb_txt.split("\n")

	header=[x for x in pdb_txt if x.startswith("HEADER")][0].split()
	pdbid=header[-1]

	try:
		depodate=header[-2]
		depodate=datetime.datetime.strptime(depodate,"%d-%b-%y")# "13-SEP-10" format
	except ValueError:
		print >>sys.stderr,"no dep-date for pdb",pdbid
		depodate=None

	#release date 
	revdates=[x.split() for x in pdb_txt if x.startswith("REVDAT")]
	structure_revdate=[x[2] for x in revdates if x[1]=="1"][0]
	structure_revdate=datetime.datetime.strptime(structure_revdate,"%d-%b-%y")# "13-SEP-10" format

	try:
		jrnlref=[x.split()[2] for x in pdb_txt if  x.startswith("JRNL") and "PMID" in x][0]
		jrnlref=int(jrnlref)
	except IndexError:
		logger.info("no journal entries for pdb %s",pdbid)
		jrnlref=None

	return {
		"pdbid":pdbid,
		"depodate":depodate,
		"releasedate":structure_revdate,
		"jrnlref":jrnlref
	}

def parse_pdb_file(pdbid):
	if os.path.isfile("pdb-entries/%s.pdb.txt"%(pdbid)):
		tgt_file = open("pdb-entries/%s.pdb.txt"%(pdbid),"r")
	elif os.path.isfile("pdb-entries/%s.txt.gz"%(pdbid)):
		tgt_file=gzip.open("pdb-entries/%s.txt.gz"%(pdbid))
	fields=parse_pdb_entry(tgt_file.read())
	tgt_file.close()
	return fields

def process_batch_parse_pdb_files(nworker=NMAXTHREADS,batch_size=500):
	global conn,cur
	conn=sqlite3.connect("local-medline-pdb.db")
	cur=conn.cursor()
	available_entries=set([x.split(".")[0] for x in os.listdir("pdb-entries/") if (os.path.isfile("pdb-entries/"+x) and not x.startswith("."))])
	cur.execute("SELECT pdbid FROM pdb")
	pdb_in_db=[x[0] for x in cur.fetchall()]
	to_insert=set(available_entries).difference(pdb_in_db)
	print len(to_insert)


	batch=sorted(to_insert)[:batch_size]
	res=process(batch,parse_pdb_file,nworker)
	res=list(res.queue)

	print "All PDB parsed, inserting into DB",len(res), [x['pdbid'] for x in res]
 	#prepare the data as an array
	values=[(x['pdbid'],x['depodate'],x['releasedate'],x['jrnlref']) for x in res if (len(x)>0) and (x['pdbid'] not in pdb_in_db)]
	print len(values)
	cur.executemany("INSERT INTO pdb(pdbid,depodate,releasedate,jrnlref) VALUES(?,?,?,?)",values)
	print "All insertions finished,commiting"

	return conn.commit()