import csv 
import json
import numpy
from numpy import array
import os.path
import re
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer


# Opening csv of PC info to gather names of PC members
# If PC member then don't require external (TODO: maybe not require external from any co-author?)
with open('eurosp2022-pcinfo.csv', newline='') as f:
    reader = csv.reader(f)
    next(reader) # skip header
    pcmembers = [row[0].lower()+' '+row[1].lower() for row in reader] # get first and last (lowercase) 


previously_declined = {} # list of previously declined requests, empty if first assignment
decliners = [] # list of papers that have declined requests in the past
# Check if there is a file for declined requests. 
if os.path.isfile("declined_reviews.csv"):
    # If the file exists, this is a re-assignement. Not all papers should be considered
    print("This is a re-assignment after declines")
    # collect the list of declines to not repeat them
    with open('declined_reviews.csv') as f:
        reader = csv.reader(f)
        next(reader) # skip header
        for row in reader:
            previously_declined[int(row[0])] = int(row[1]) # key = paper that does not have reviewer, value = paper that declined
            decliners = decliners + [int(row[1])]
else:
    print("This is a new assignment")

print (previously_declined.keys())



# Opening JSON file with information from all papers
j = open('eurosp2022-data.json', encoding="utf8")
# returns JSON object as a dictionary
data = json.load(j)
 
# create a dict with papers with the following fields
# pid
# title
# abstract
# topics
# authors and affiliations
# collaborators
papers = {}
cnt = 150     # DEBUGGING: counter to test on small number of papers

for p in data:
    # DEBUGGING: counter to test on small number of papers
    cnt = cnt-1
    if cnt ==0: break

    pid = p['pid']

    papers[pid] = {}
    
    # parse title
    papers[pid]['title'] = p['title']


    # parse abstract
    papers[pid]['abstract'] = p['abstract']
    
    # parse topics 
    papers[pid]['topics'] =  p['topics']


    # parse authors
    papers[pid]['authors'] = [] # list of authors names (first last, lower case)
    papers[pid]['affiliations'] = [] # list of affiliations name
    for i,author in enumerate(p['authors']):

        # Get information about the person that will review
        # We assume that the first author is always the one handling the review *unless* the first author is in the Program Committee
        # We assume that the second author is not in the PC. If both are, need to rethink this conditional
        if (i==0 and (author['first'].lower()+" "+author['last'].lower() not in pcmembers)) or (i==1 and (p['authors'][0]['first'].lower()+" "+p['authors'][0]['last'].lower() in pcmembers)):
            papers[pid]['reviewer_first'] = author['first']
            papers[pid]['reviewer_last'] = author['last']
            papers[pid]['reviewer_email'] = author['email']

        # 
        papers[pid]['authors'] = papers[pid]['authors'] + [author['first'].lower()+' '+author['last'].lower()]
        if 'affiliation' in author:
            papers[pid]['affiliations'] = papers[pid]['affiliations'] + [author['affiliation'].lower()]
    

    # parse collaborators
    papers[pid]['collab_affiliation'] = [] # list of collaborators affiliations
    papers[pid]['collab_names'] = [] # list of collaborators names (first last, lower case)

    if 'collaborators' in p:
        for element in p['collaborators'].splitlines():
            if 'all' in element.lower():  # ALL (institution)                      
                papers[pid]['collab_affiliation'] = papers[pid]['collab_affiliation'] + [re.findall(r'\((.*?)\)', element.lower())[0].replace("the ", "")]

            
            else: # Author (institution) -- ignore institutions. False conflicts due to name repetitions should not matter, plenty of reviewers available!
                papers[pid]['collab_names'] = papers[pid]['collab_names'] + re.findall(r'(.*?)\s*\(', element.lower())


j.close()
print("Gathered data from all papers \n")


# Now assign scores to papers
mapping={}

if not previously_declined: 
    # if previously_declined is empty and this is a fresh assignment
    # we need scores for all combinations
    score = numpy.zeros((len(papers), len(papers)))
else:
    # if this is a re-assignment, we only need scores for the papers without reviewers
    score = numpy.zeros((len(previously_declined), len(papers)))

c_paper = 0 # counter for rows
cnt = 0 # counter for printout

for (pid,paper) in papers.items(): #loop over papers to be reviewed
    
    if cnt % 20 == 0: print ("Assigned score to %d papers out of %d" % (cnt, len(papers)))
    c_reviewer = 0 # counter for columns

    # check if this paper is already assigned
    if pid not in previously_declined.keys():
        # if the paper has not been declined 
        # or if the list is empty (first assignment)
        # then don't consider it for giving scores
        #print ("I am not assigning paper ", pid)
        cnt += 1
        continue 

    for (pid_r,paper_r) in papers.items(): # loop over reviewers
        mapping[(c_paper,c_reviewer)] = (pid,pid_r) # create variable for easy indexing
     
        #if pid == pid_r:
        if c_paper == c_reviewer:
            c_reviewer +=1
            continue # a paper should not be assigned to itself -- we leave its score to zero

        # We check that there are no conflicts
        # (1) reviewer authors are not from affiliations in conflicts declared by authors to be reviewed
        if sum(1 for i in paper['collab_affiliation'] if (sum(1 for j in paper_r['affiliations'] if i in j) >0 or sum(1 for j in paper_r['affiliations'] if j in i) >0)) >0 :
            c_reviewer +=1
            continue # a paper with conflict should not be assigned -- we leave the score to zero

       
        # We check that there are no conflicts
        # (2) authors are not from affiliations in conflict declared by reviewer authors
        if sum(1 for i in paper_r['collab_affiliation'] if (sum(1 for j in paper['affiliations'] if i in j) >0 or sum(1 for j in paper['affiliations'] if j in i) >0)) >0 :
            c_reviewer +=1
            continue # a paper with conflict should not be assigned -- we leave the score to zero


        # (3) reviewer authors are not listed as individual conflicts by authors to be reviewed
        if sum(1 for i in paper['collab_names'] if i in paper_r['authors']) >0:
            c_reviewer +=1
            continue # a paper with conflict should not be assigned -- we leave the score to zero


        # (4) authors are not listed as individual conflicts by reviewer authors
        if sum(1 for i in paper_r['collab_names'] if i in paper['authors']) >0:
            c_reviewer +=1
            continue # a paper with conflict should not be assigned -- we leave the score to zero

        # (5) reviewer authors are not authors of paper to be reviewed
        if sum(1 for i in paper['authors'] if i in paper_r['authors']) >0:
            c_reviewer +=1
            continue # a paper with conflict should not be assigned -- we leave the score to zero


        # (6) reviewer authors are not from the same affiliations as the authors
        if sum(1 for i in paper['affiliations'] if (sum(1 for j in paper_r['affiliations'] if i in j) >0 or sum(1 for j in paper_r['affiliations'] if j in i) >0)) >0 :
            c_reviewer +=1
            continue # a paper with conflict should not be assigned -- we leave the score to zero

        # (7) reviewer authors already have declined this assignment
        if previously_declined[pid] == pid_r:
            c_reviewer += 1
            continue # a paper with conflict should not be assigned -- we leave the score to zero


        ## if there are no conflicts    

        # papers receive quarter point per coincidence in topic
        score[c_paper, c_reviewer] -= sum(0.25 for i in paper['topics'] if i in paper_r['topics'])

        if pid_r in decliners:
            print("Paper %d is a decliner, increasing score" % (pid_r))
            score[c_paper, c_reviewer] -= 0.25

        # papers receive  for similarity in abstract
        vect = TfidfVectorizer(min_df=1, stop_words="english")   
        tfidf = vect.fit_transform([paper['abstract'],paper_r['abstract']])   
        pairwise_similarity = tfidf * tfidf.T 

        score[c_paper, c_reviewer] -= pairwise_similarity[0,1]     

        c_reviewer +=1
    c_paper += 1
    cnt += 1 # counter for printout


print("Computed scores for all papers that need reviews, launching matching algorithm...\n")

from scipy.optimize import linear_sum_assignment
row_ind, col_ind = linear_sum_assignment(score)

print("Assignment produced")


f_abstracts=open('external_assignment.txt', 'w') # file with info about the assignments for human check (mapping of abstracts)

f_mapping = open('external_matching.csv','w') # file with the mapping to be recovered later
f_mapping.write('pid_reviewed, pid_reviewer\n') # header for matching CSV

f_bulk_assignment = open('externals_bulk_assignment.txt' , 'w') # file with assignments to be uploaded in HotCRP (Assignments -> Bulk Update)
f_bulk_assignment.write('paper,assignment,email,reviewtype\n') # header for HotCRP

f_bulk_usernames = open('externals_bulk_users.txt', 'w') # file to create users with names to be uploaded in HotCRP (Users->New User->Bulk update)
f_bulk_usernames.write('name,email,add_tags\n') # header for HotCRP

for i,c in enumerate(col_ind):
    paper, reviewer = mapping[(i,c)] # paper=pid of paper to be reviewed; reviewer=pid of paper of reviewer

    # create file with mapping
    f_mapping.write("%s, %s \n" % (paper, reviewer))

    # create Info file
    f_abstracts.write("Paper '%s' (#%d) reviews paper '%s' (#%d)\n" % (papers[reviewer]['title'],reviewer, papers[paper]['title'], paper))
    f_abstracts.write("-"*20+"\n" ) 
    f_abstracts.write("Abstract #%d:   %s\n\n" % (reviewer, papers[reviewer]['abstract'].replace('\n','')))
    f_abstracts.write("Abstract #%d:   %s\n" % (paper, papers[paper]['abstract'].strip()))
    f_abstracts.write("="*60+"\n\n" ) 

    # create Bulk Assignment and Bulk Users files
    f_bulk_assignment.write('%d,review,%s,external\n' % (paper,papers[reviewer]['reviewer_email'])) # for each paper the email of the chosen reviewer 
    f_bulk_usernames.write('%s %s, %s, %s\n' % (papers[reviewer]['reviewer_first'], papers[reviewer]['reviewer_last'], papers[reviewer]['reviewer_email'], "external_reviewer")) # for each chosen reviewer also update name 

# Closing file
f.close()



