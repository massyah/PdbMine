Getting info per authors 
============================

# Installation

uncompress the db: 

    bunzip2  author_index.cpickle.bdat.bz2


# Determine target authors list

Populate the author_list.tsv file with target authors, format is key <TAB> list of full first and last name

To get the list of full first and last name, run get_author_variants. Variants for each key in author_list.tsv will be printed to the console. Edit this list accordingly and add entries in author_list.tsv

# Get data by authors
run [author_search.py], output will be appended to author_search.csv
Run analyze_pdb_for_pmids.R.
This will perform the join with the pdb data and will save its output in author_search_with_pdb_data.tsv. 



# author index 
database can be updated with build_author_index.py 