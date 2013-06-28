import urllib2
import logging
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
	ftp = ftplib.FTP("ftp.wwpdb.org")
	ftp.login("massyah@gmail.com","none")
	ftp.cwd("/pub/pdb/data/structures/all/pdb")
	logger.info("Initiated connection, CWD successful")

	success=0
	for entry in pdb_ids:
		file=open("pdb-entries/%s.txt.gz"%(entry),"w")
		ftp.retrbinary("RETR pdb%s.ent.gz"%(entry.lower()),file.write)
		file.close()
		logger.info("Downloaded %s",entry)
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
				print "Still",self.in_queue.qsize(),"to do"
			except Exception as e:
				print "exception in thread:",e
				return

def process(data, function, num_workers=1):
	in_queue = Queue()
	for item in data:
		in_queue.put(item)
	out_queue = Queue(maxsize=in_queue.qsize())
	workers = [Worker(function, in_queue, out_queue) for i in xrange(num_workers)]
	for worker in workers: 
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



def process_batch_download(nworker=NMAXTHREADS,batch_size=500):
	# Filter out the one already downloaded
	parse_citations()
	available_entries=set([x.split(".")[0] for x in os.listdir("pdb-entries/")])
	pdb_ids_to_get=set(all_pdb_ids).difference(available_entries)
	print "To get",len(pdb_ids_to_get)
	# Take some pdbid to download, split them in lists 

	pdb_ids_to_get=sorted(pdb_ids_to_get)
	batches=[]
	for i in range(0,len(pdb_ids_to_get),batch_size):
		batches.append(pdb_ids_to_get[i:i+batch_size])
	process(batches,ftp_download_entries,nworker)


## Parsing the files in multi-threaded way 
def parse_pdb_file(pdbid):
	with open("pdb-entries/%s.pdb.txt"%(pdbid),"r") as f:
		fields=pdb_parse_entry(f.read())
	return fields

def process_batch_pdb_files(nworker=NMAXTHREADS,batch_size=500):
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

 	#prepare the data as an array
	values=[(x['pdbid'],x['depodate'],x['releasedate'],x['jrnlref']) for x in res]
	cur.executemany("INSERT INTO pdb(pdbid,depodate,releasedate,jrnlref) VALUES(?,?,?,?)",values)
	conn.commit()