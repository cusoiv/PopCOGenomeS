import os
import sys
import numpy

## Collect parameters
project_dir = ""
input_contig_dir = ""
contig_dir = ""
contig_extension = ""
output_prefix = ""
pop_infile_name = ""
ref_iso = ""
ref_contig = ""
len_block_threshold = 0
gap_prop_thresh = 0.0
phyML_loc = ""
phyML_properties = ""




parameter_file = open("phybreak_parameters.txt","r")
for line in parameter_file:
	line = line.strip().split(" = ")
	if len(line) > 1:
		if line[0] == "project_dir":
			project_dir = line[1].split(" #")[0]
		elif line[0] == "input_contig_dir":
			input_contig_dir = line[1].split(" #")[0]
		elif line[0] == "contig_dir":
			contig_dir = line[1].split(" #")[0]
		elif line[0] == "input_contig_extension":
			contig_extension = line[1].split(" #")[0]
		elif line[0] == "output_prefix":
			output_prefix = line[1].split(" #")[0]
		elif line[0] == "pop_infile_name":
			pop_infile_name = line[1].split(" #")[0]
		elif line[0] == "ref_iso":
			ref_iso = line[1].split(" #")[0]
		elif line[0] == "ref_contig":
			ref_contig = line[1].split(" #")[0]
		elif line[0] == "len_block_threshold":
			len_block_threshold = int(line[1].split(" #")[0])
		elif line[0] == "gap_prop_thresh":
			gap_prop_thresh = float(line[1].split(" #")[0])
		elif line[0] == "phyML_loc":
			phyML_loc = line[1].split(" #")[0]
		elif line[0] == "phyML_properties":
			phyML_properties = line[1].split(" #")[0]



parameter_file.close()

#these directories will generate if they do not already exist
input_dir = project_dir+"align/"
alignment_dir = input_dir+"alignment_blocks/"


#these are output file names
strain_list_filename = "strain_names.txt"
MSA_name = output_prefix+".core.fasta"
phy_prefix = output_prefix
block_loc_filename = output_prefix+".block_location.txt"


#############   FUNCTIONS   #############
def poly_count(msa_dict,loc):
	nt_dict = {'A':0,'C':0,'G':0,'T':0}
	for seq in msa_dict:
		nt = msa_dict[seq][loc]
		if nt != "N":
			nt_dict[nt] += 1
	poly = 0
	for nt in nt_dict:
		count = nt_dict[nt]
		if count > 1:
			poly += 1
	return poly

def remove_N_only_gaps(msa_dict):
	nt_dict = {}#{'N':0,'-':0}
	for strain in msa_dict:
		seq = msa_dict[strain]
		for i in range(0,len(seq)):

			try:
				nt_dict[i]
			except:
				nt_dict[i] = {'N':0,'-':0,'nt':0}
			nt = seq[i]
			if nt == '-':
				nt_dict[i]['-'] += 1
			elif nt == 'N':
				nt_dict[i]['N'] += 1
			else:
				nt_dict[i]['nt'] += 1
	seq_num = len(msa_dict)
	remove_sites = []
	for nt in nt_dict:
		count = nt_dict[nt]
		if nt_dict[i]['nt'] <= 1:
			remove_sites.append(nt)
	out_dict = {}
	for strain in msa_dict:
		seq = msa_dict[strain]
		out_dict[strain] = ''
		for i in range(0,len(seq)):
			if i not in remove_sites:
				out_dict[strain] += seq[i]
	return out_dict

#################   MAIN   #################
if os.path.isdir(alignment_dir) == False:
	os.makedirs(alignment_dir)

#make list of strains
infile = open(project_dir+strain_list_filename,"r")
isolist = []
for line in infile:
	line = line.strip()
	isolist.append(line)
infile.close()
#print(isolist)

num = 0
iso = ""
seqdict = {}
for iso in isolist:
	seqdict[iso] = ""
temp_seqdict = {}
lenseq = 0

ref_order = []

infile = open(input_dir+output_prefix+".maf","r")
temp_seq_list = []
label = 0
multi = 0
wr = 0 #swtich for writing
for line in infile:
	if line == "\n":
		for iso in isolist:
			if iso not in temp_seq_list:
				wr = 0
				#print(iso)
				break
			else:
				wr = 1
		if wr == 1:
			#print(label)
			for iso in isolist:
				seq = temp_seqdict[iso]
				try:
					seqdict[label][iso] = seq
				except:
					seqdict[label] = {}
					seqdict[label][iso] = seq
		temp_seq_list = []
	elif line[0] == 'a':
		line = line.strip()
		mult = int(line.split("mult=")[1])
		try:
			label = int(line.split(" mult=")[0].split("label=")[1])
		except:
			label = line.split(" mult=")[0].split("label=")[1]
	elif line[0] == 's':
		line = line.strip()
		iso = line.split(".")[0].split(" ")[1]
		contig = line.split(".")[1].split("\t")[0]
		seq = line.split(" ")[5]
		
		temp_seq_list.append(iso)
		temp_seqdict[iso] = seq
		lenseq = len(seq)
		
		if contig == ref_contig:
			start = int(line.split("\t")[2].split(" ")[0])
			length = int(line.split("\t")[2].split(" ")[1])
			direc = line.split("\t")[2].split(" ")[3]
			if direc != "+":
				start = start+length
			tup = (start,label)
			ref_order.append(tup)
ref_order.sort()
#Thus seqdict is a dictionary with labels(MSA alignments maf code number) as keys and their corresponding values are all the sequences in this alignment
print("Done reading .maf file. Starting alignment filtering.")
#print(ref_order)
#print (len(seqdict))

#for key, value in seqdict.items() :
#    print (key, len(value))
#remove sites that contain either only Ns, or sequence from a single genome
for label in seqdict:
	seqdict[label] = remove_N_only_gaps(seqdict[label])
#filter the alignment blocks to remove short blocks and blocks with high number
#of gaps, then remove all gap containing columns from the sequence alignments

label_sizes = {}
use_labels = []

for label in ref_order:
	start = label[0]
	label = label[1]
	try:
		ref_seq = seqdict[label][ref_iso]
		len_ref_seq = len(ref_seq)
		gapless_ref_seq = ref_seq.replace("-","")
		len_gapless_ref_seq = len(gapless_ref_seq)
		gap_prop = float(len_gapless_ref_seq)/float(len_ref_seq)
		
		if len_gapless_ref_seq >= len_block_threshold:
			if gap_prop >= gap_prop_thresh:
				use_labels.append(label)
				label_sizes[label] = {}
				label_sizes[label]["raw"] = len_ref_seq
				label_sizes[label]["degap"] = len_gapless_ref_seq
				label_sizes[label]["SNPcount"] = 0
	except:
		pass
print("Done filtering, finding gap-columns and SNP locations in alignment.")
#print(label_sizes)

#make the no-gap and SNP location lists
a = 0
writedict = {}
snplist = {}
snpcount = 0
nt = []
for label in use_labels:
	snpcount = 0
	nt = []
	ref_seq = seqdict[label][ref_iso]
	len_ref_seq = len(ref_seq)
	for i in range(0,len_ref_seq):
		a = 0
		nt = []
		for iso in isolist:
			resi = seqdict[label][iso][i]
			if resi == "-":
				a = 1
			else:
				nt.append(resi)
		if a == 0:
			nt = list(set(nt))
			try:
				writedict[label][i] = ""
			except:
				writedict[label] = {}
				writedict[label][i] = ""
			if len(nt) > 1:
				snpcount += 1
	label_sizes[label]["SNPcount"] = snpcount
	#print(str(label)+"\t"+str(snpcount))


print("Done finding gap-columns and counting SNPs")
#print(writedict)
#print(snplist)

degap_seqdict = {}
for label in use_labels:
	for j in range(0,len(isolist)):
		iso = isolist[j]
		seq = seqdict[label][iso]
		ref_seq = seqdict[label][ref_iso]
		len_ref_seq = len(ref_seq)
		try:
			degap_seqdict[iso][label] = ""
			for k in range(0,len_ref_seq):
				try:
					st = writedict[label][k]
					degap_seqdict[iso][label] += seq[k]
				except:
					pass
		except:
			degap_seqdict[iso] = {}
			degap_seqdict[iso][label] = ""
			for k in range(0,len_ref_seq):
				try:
					st = writedict[label][k]
					degap_seqdict[iso][label] += seq[k]
				except:
					pass
print("Done removing gap-columns")
#print(degap_seqdict)

#re-iterate over the use_labels list
temp_use_labels = []
for label in use_labels:
	len_gapless_ref_seq = len(degap_seqdict[ref_iso][label])
	len_ref_seq = len(seqdict[label][ref_iso])
	gap_prop = float(len_gapless_ref_seq)/float(len_ref_seq)
	if len_gapless_ref_seq >= len_block_threshold and gap_prop >= gap_prop_thresh:
		label_sizes[label]["raw"] = len_ref_seq
		label_sizes[label]["degap"] = len_gapless_ref_seq
		temp_use_labels.append(label)
use_labels = list(set(temp_use_labels))
del temp_use_labels

#make the full, degapped sequences and write the start:stop location of each block in the sequence
print("Writing information about alignment blocks to file.")
full_seqdict = {}
loc = 0
block_loc = open(input_dir+block_loc_filename,"w")
block_loc.write("Label\tStart\tLocation_in_block_start\tLocation_in_block_stop\n")
for iso in degap_seqdict:
	for i in range(0,len(ref_order)):
		label = ref_order[i][1]
		start = ref_order[i][0]
		if label in use_labels:
			seq = degap_seqdict[iso][label]
			try:
				full_seqdict[iso] += seq
			except:
				full_seqdict[iso] = seq
			if iso == ref_iso:
				block_loc.write(str(label) +"\t"+ str(start) +"\t"+ str(loc) +"\t"+ str(loc+len(seq)) +"\n")
				loc = loc+len(seq)
block_loc.close()
#print(full_seqdict)

#write the full, degapped sequences
corefile = open(input_dir+MSA_name,"w")
for k in range(0,len(isolist)):
	iso = isolist[k]
	corefile.write(">"+iso +"\n"+ full_seqdict[iso] +"\n")
corefile.close()



