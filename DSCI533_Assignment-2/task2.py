from pyspark import SparkContext
import os
import sys
import math
import time
import csv
from collections import OrderedDict
import itertools

os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable

# Path
input_path_val = r"C:\Users\ankus\PycharmProjects\DSCI553_Assignment2\publicdata\ta_feng_all_months_merged.csv"
output_path_val = r"output_file_sc.txt"
support=50
filter_threshold=20
Preprocessed_file=r"Customer_product.csv"


start_time2 = time.time()
sc = SparkContext('local[*]', 'AssignmentTwo_Task')




def create_Single_element(p_threshold, cluster):
    dict_elem={}
    final_elem= []
    for i in cluster:
        temp_el=set(i)
        for j in temp_el:
            if j not in dict_elem:
                dict_elem[j]=0
            dict_elem[j]+=1
    for k in dict_elem.keys():
        if dict_elem[k]>=p_threshold:
            final_elem.append(k)
    return sorted(final_elem)





def Candidate_list_Generator(current, k, cluster_list):
    res=set()
    tempdoubles=set()
    # print(current)
    if k==2:
        for item in current:
            #print(item)
            tempdoubles.add(item)

    for item in cluster_list:
        if k==2:
            common_set=set(item).intersection(tempdoubles)
        else:
            #print("Item current_list", set(item))
            #print("Current_list", set(current))
            common_set = set(item).intersection(set(current))
            #if k!=2 and common is not set():
            #    print("-------------------------------------------",common)

        common_set=sorted(common_set)
        for comb in itertools.combinations(common_set,k):
            #print(len(comb))
            res.add(frozenset(sorted(comb)))
    #print("************************************",res)
    return res


def apriori_Algo(p_threshold,cluster_list):
    single_el_list=create_Single_element(p_threshold,cluster_list)
    current_set=set(single_el_list)
    #print("//////////////////////////", single_el_list)
    candidate_dict={}
    pair_size=1
    while len(single_el_list)!=0:
        candidate_dict[pair_size] = single_el_list
        pair_size += 1
        single_el_list = Candidate_list_Generator(current_set, pair_size,cluster_list)
        #if pair_size==3:
        #    print(single_el_list)
        final_single_el_list = []
        count_el=dict()
        for i in cluster_list:
            for j in single_el_list:
                if set(j).issubset(i):
                    if j not in count_el:
                        count_el[j] = 0
                    count_el[j]+= 1
        current_set=set()
        for key in count_el.keys():
            if count_el[key] >= p_threshold:
                #print("//////////////////////////",set(key))
                current_set=current_set.union(set(key))
                final_single_el_list.append(frozenset(sorted(key)))
        #print(("//////////////////////////", final_single_el_list))
        single_el_list = final_single_el_list
        #print("//////////////////////////", candidate_dict)

    return candidate_dict


def create_candidates_set(x,n_size_data,threshold):
    individual_cluster_list = list(x)
    p_threshold = math.ceil(threshold*(len(individual_cluster_list) / n_size_data))
    set_after_apriori=apriori_Algo(p_threshold,individual_cluster_list)
    #print(set_after_apriori)
    Fans=set()
    for el_key in set_after_apriori.keys():
        for each_val in set_after_apriori[el_key]:
            if el_key==1:
                Fans.add(tuple(frozenset({each_val})))
            else:
                Fans.add(tuple(each_val))
    return Fans


FileRDD = sc.textFile(input_path_val).map(lambda x: x.split(","))
print(len(FileRDD.collect()))
column_head = FileRDD.take(1)[0]
FileRDD = FileRDD.filter(lambda x: x != column_head and x != "").map(lambda x: [x[0].strip('"') + "-" + str(int(x[1].strip('"'))), str(int(x[5].strip('"')))])
heading = ['DATE-CUSTOMER_ID','PRODUCT_ID']



with open(Preprocessed_file, 'w') as csvfile:
    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(heading)
    csvwriter.writerows(FileRDD.collect())


start_time = time.time()
FileRDD = sc.textFile(Preprocessed_file).cache()

#print(len(FileRDD.collect()))
column_head = FileRDD.take(1)[0]
#print(column_head)
RDDFile = FileRDD.filter(lambda x: x != column_head and x != "")
#RDDFile = RDDFile.filter(lambda x: x != "")


RDDFile = RDDFile.map(lambda x:x.split(",")).map(lambda x:(x[0],str(int(x[1])))).groupByKey().filter(lambda x: len(x[1]) > int(filter_threshold)).map(lambda x:list(set(x[1])))
#print(RDDFile.collect())


n_size_data = RDDFile.count()
#candidates=RDDFile.partitionBy(2).map(lambda x: create_candidates_set(x, n_size_data)).distinct()


candidates=RDDFile.mapPartitions(lambda x: create_candidates_set(x, n_size_data, support)).distinct().collect()
#print("candidates \n",len(candidates))


def Phase_two_mapcandidate(x,candidates):
        individual_cluster_list = list(x)
        Fans = dict()
        for el_candidate in candidates:
            count=0
            for each_el_x in individual_cluster_list:
                if set(el_candidate).issubset(set(each_el_x)):
                    count += 1
            Fans[el_candidate]=count
        Fans_List=[(candidate_el,Fans[candidate_el]) for candidate_el in Fans.keys()]
        return Fans_List



new_candidates_map_two=RDDFile.mapPartitions(lambda x:Phase_two_mapcandidate(x,candidates))
#print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%",new_candidates_map_two.collect())
new_candidate_reduce_two= new_candidates_map_two.reduceByKey(lambda a,b : a+b).filter(lambda x: x[0] if x[1] >= int(support) else None).collect()
#print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@",len(new_candidate_reduce_two))

final_candidate_reduce_first=dict()
for i in candidates:
    temp2=sorted(i)
    lentemp2=len(i)
    if lentemp2 not in final_candidate_reduce_first:
        final_candidate_reduce_first[lentemp2]=[]
    if temp2 not in final_candidate_reduce_first[lentemp2]:
        final_candidate_reduce_first[lentemp2].append(temp2)
        final_candidate_reduce_first[lentemp2]=sorted(final_candidate_reduce_first[lentemp2])

final_candidate_reduce_dict=dict()
for i in new_candidate_reduce_two:
    temp3=sorted(i[0])
    lentemp3=len(i[0])
    if lentemp3 not in final_candidate_reduce_dict:
        final_candidate_reduce_dict[lentemp3]=[]
    if temp3 not in final_candidate_reduce_dict[lentemp3]:
        final_candidate_reduce_dict[lentemp3].append(temp3)
        final_candidate_reduce_dict[lentemp3]=sorted(final_candidate_reduce_dict[lentemp3])

#print("~~~~~~~~~~~~~~~~~~~~~162~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~",final_candidate_reduce_first)
#print("~~~~~~~~~~~~~~~~~~~~~~163~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~",final_candidate_reduce_dict)

#======================================Write========================================================

f = open(output_path_val, 'w+')

def printing_function(value):
    printFlag, printFlag_1 = 0, 0
    for i in value:
        if len(i) == 1: #To avoid "," in i
            if printFlag_1 == 0:
                f.write("('" + str(i[0]) + "')")
                printFlag_1 = 1
            else:
                f.write(",")
                f.write("('" + str(i[0]) + "')")
        else:
            if printFlag == 0:
                f.write(str(tuple(i)))
                printFlag = 1
            else:
                f.write(",")
                f.write(str(tuple(i)))
    f.write("\n\n")


f.write("Candidates:\n")
temp=sorted(final_candidate_reduce_first.keys())
for key in temp:
    value=final_candidate_reduce_first[key]
    #value.sort()
    printing_function(value)

f.write("Frequent Itemsets:\n")
temp=sorted(final_candidate_reduce_dict.keys())
for key in temp:
    value = final_candidate_reduce_dict[key]
    #value.sort()
    printing_function(value)

end_time = time.time()
print("Duration: ", end_time - start_time)
print("Duration: ", end_time - start_time2)
