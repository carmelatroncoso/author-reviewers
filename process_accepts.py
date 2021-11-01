# Python program to read
# json file
 
import json
import csv
import os.path


# Opening JSON file with information from all papers
j = open('eurosp2022-data.json', encoding="utf8")
 # returns JSON object as a dictionary
data = json.load(j)
# create a list of all submitted papers papers
# pid
submissions = []
for p in data:
    submissions = submissions + [int(p['pid'])]

number_of_submissions = float(len(submissions))



# Opening csv of previous matching
reviewed_by = {} # dictionary with key paper reviewed, and value assigned reviewer
with open('external_matching.csv') as f:
    # 
    reader = csv.reader(f)
    next(reader) # skip headers
    for row in reader:
        reviewed_by[int(row[0])] = int(row[1])



# Opening csv of log actions to collect accept and decline
papers = {}
with open('eurosp2022-log.csv', newline='') as f:
    reader = csv.reader(f)
    next(reader) #skip headers
    
    for row in reader: 
        # format of csv
        # date, email, affected_email, via, paper, action
        date, paper, decision = row[0], int(row[4]), row[5]

        # We filter all records in the CSV that are not about external invites decision
        if not ("accept" in decision or "decline" in decision): 
            #print ("Record not about externals: ", paper, decision)
            continue

        papers[paper]=papers.get(paper,("1977-09-28 23:17:58 America/New_York","none")) # if we still don't have any record in the paper, we ensure that the default status will always be overwritten (all dates are after)

        if date > papers[paper][0]: # if the record is older than the one we have, we update the decision
            papers[paper]=(date,"accept" if "accept" in decision else "decline")
            submissions.remove(paper)


accepts = 0
declines = 0
declined_list = []
for paper,value in papers.items():
    #print (paper, value)
    if value[1] == "accept":
        accepts=accepts+1  
    else: 
        declines = declines+1
        declined_list = declined_list + [paper]

total = float(accepts + declines)

print("Requests: %d, Accepted %d (%f), Reject %d (%f), Answered %d (%f)\n" % (number_of_submissions, accepts, accepts/number_of_submissions, declines, declines/number_of_submissions, total, total/number_of_submissions))
print("Papers whose authors declined the invitation:", [reviewed_by[paper] for paper in declined_list])
print("Papers that were left without reviewer:", declined_list)
print("Papers whose authors did not answer: ", [reviewed_by[paper] for paper in submissions])
print("Papers we don't know if they have a reviewer: ", submissions)


# create file with papers that need to be reassigned, and assignments that should not be repeated
# check if there is already a file for declined requests, new declines should be added
if os.path.isfile("declined_reviews.csv"):
    f = open("declined_reviews.csv", 'a')
else:
    f = open("declined_reviews.csv", 'w')
    f.write('pid_reviewed, pid_reviewer\n') # header for matching CSV
   
# add papers from declined requests   
for (paper, reviewer) in zip(declined_list,[reviewed_by[paper] for paper in declined_list]):
    f.write("%s, %s \n" % (paper, reviewer))

# add papers from unanswered requests
for (paper, reviewer) in zip(submissions,[reviewed_by[paper] for paper in submissions]):
    f.write("%s, %s \n" % (paper, reviewer))


f.close()




