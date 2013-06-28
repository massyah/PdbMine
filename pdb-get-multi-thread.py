import urllib2
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
				print "Will get",data
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



def process_batch(nworker=NMAXTHREADS,batch_size=500):
	# Filter out the one already downloaded
	available_entries=set([x.split(".")[0] for x in os.listdir("pdb-entries/")])
	pdb_ids_to_get=set(all_pdb_ids).difference(available_entries)
	print "To get",len(pdb_ids_to_get)
	# Take some pdbid to download
	batch=sorted(pdb_ids_to_get)[:batch_size]
	process(batch,pdb_download_entry,nworker)


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