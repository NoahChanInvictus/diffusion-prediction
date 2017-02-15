# -*-coding:utf-8-*-

import sys
import math
import pickle
from elasticsearch import Elasticsearch
from feature_user_profile import user_fansnum
import json

reload(sys)
sys.path.append("../../")
from global_utils import es_flow_text, es_prediction, r_micro
from global_config import minimal_time_interval, pre_flow_text, type_flow_text, data_order, K,
                            index_manage_prediction_task, type_manage_prediction_task, index_type_prediction_task
from time_utils import ts2datetime, datetime2ts, ts2date

# featrues are stored in task es with index_name of task_name 
# event is used to search weibo from es_prediction with event index_name
# update time is current ts, start_ts = current_ts - 3600


def organize_feature(task_name, event, start_ts, end_ts):
    data = []
    index_list = []
    task_name = "micro_prediction_" + task_name


    while 1:
        data_dict = dict()
        if start_ts > end_ts:
            break
        results_list = user_fansnum(event, start_ts, start_ts+minimal_time_interval)
        for i in range(len(data_order)):
            data_dict[data_order[i]] = results_list[i]
        data_dict["update_time"] = start_ts+minimal_time_interval
        start_ts += minimal_time_interval
        print start_ts
        es_prediction.index(index=task_name, doc_type=index_type_micro_task, id=start_ts, body=data_dict)

    #data_list = [total_fans_list,total_origin_list,total_retweet_list,total_comment_list,positive_count_list,neutral_count_list,negetive_count_list,origin_important_user_count,origin_important_user_retweet,retweet_important_user_count,retweet_important_user_retweet, total_count,average_origin_imp_hour_list,average_retweet_imp_hour_list]
    #y_value = total_count

    print item.encode("utf-8")


# search the lastest 12 time interval data
# organise data feature

def dispose_data(task_name,current_ts):
    origin_task_name = task_name
    task_name = "micro_prediction_" + task_name
    query_body = {
        "query": {
            "match_all":{}
        },
        "size": K,
        "sort":{"update_time":{"order":"desc"}}
    }

    sort_query_body = {
        "query": {
            "range":{
                "update_time":{
                    "lte": current_ts
                }
            }
        }
    }

    total_count = []
    total_fans_list = []
    total_origin_list = []
    total_retweet_list = []
    total_comment_list = []
    positive_count_list = []
    neutral_count_list = []
    negetive_count_list = []
    origin_important_user_count = []
    origin_important_user_retweet = []
    retweet_important_user_count = []
    retweet_important_user_retweet = []
    average_origin_imp_hour = 0
    average_retweet_imp_hour = 0
    average_origin_imp_hour_list = []
    average_retweet_imp_hour_list = []

    feature_list = []
    results = es_prediction.search(index=task_name, doc_type=index_type_micro_task, body=query_body)["hits"]["hits"]
    location = es_prediction.count(index=task_name, doc_type=index_type_micro_task, body=sort_query_body)["count"]

    if len(results) != K:
        short_len = K - len(results)
        results.extend([[]]*short_len)
    results.reverse()
    for item in results:
        if item:
            item = item["_source"]
            total_fans_list.append(item["total_fans_number"])
            total_origin_list.append(item["origin_weibo_number"])
            total_retweet_list.append(item["retweeted_weibo_number"])
            total_comment_list.append(item["comment_weibo_number"])
            positive_count_list.append(item["positive_weibo_number"])
            neutral_count_list.append(item["neutral_weibo_number"])
            negetive_count_list.append(item["negetive_weibo_number"])
            origin_important_user_count.append(item["origin_important_user_number"])
            origin_important_user_retweet.append(item["origin_important_user_retweet"])
            retweet_important_user_count.append(item["retweet_important_user_count"])
            retweet_important_user_retweet.append(item["retweet_important_user_retweet"])
            average_origin_imp_hour_list.append(item["average_origin_imp_hour"])
            average_retweet_imp_hour_list.append(item["average_retweet_imp_hour"])
            total_count.append(item["total_count"])
        else:
            total_fans_list.append(0)
            total_origin_list.append(0)
            total_retweet_list.append(0)
            total_comment_list.append(0)
            positive_count_list.append(0)
            neutral_count_list.append(0)
            negetive_count_list.append(0)
            origin_important_user_count.append(0)
            origin_important_user_retweet.append(0)
            retweet_important_user_count.append(0)
            retweet_important_user_retweet.append(0)
            average_origin_imp_hour_list.append(0)
            average_retweet_imp_hour_list.append(0)
            total_count.append(0)

    # feature
    feature_list.append(location)
    for each in total_fans_list:
        feature_list.append(math.log(int(each)+1))
    for each in origin_important_user_retweet:
        feature_list.append(math.log(int(each)+1))
    for each in retweet_important_user_retweet:
        feature_list.append(math.log(int(each)+1))

    for i in range(len(total_origin_list)):
        feature_list.append(math.log(int(each)+1))
        feature_list.append(float(each)/(1+total_count[i]))
    for i in range(len(total_retweet_list)):
        feature_list.append(math.log(int(each)+1))
        feature_list.append(float(each)/(1+total_count[i]))
    for i in range(len(total_comment_list)):
        feature_list.append(math.log(int(each)+1))
        feature_list.append(float(each)/(1+total_count[i]))

    feature_list.extend(positive_count_list)
    feature_list.extend(neutral_count_list)
    feature_list.extend(negetive_count_list)
    feature_list.extend(origin_important_user_count)
    feature_list.extend(retweet_important_user_count)
    feature_list.extend(total_count)
    feature_list.extend(average_origin_imp_hour_list)
    feature_list.extend(average_retweet_imp_hour_list)


    # load model and prediction
    if total_count[-1] >= 100:
        with open("micro-prediction-up.pkl","r") as f:
            gbdt = pickle.load(f)
    else:
        with open("micro-prediction-down.pkl", "r") as f:
            gbdt = pickle.load(f)

    pred = gbdt.predict(feature_list)
    for item in pred:
        prediction_value = item
        prediction_value = math.exp(prediction_value)
        print prediction_value


    # update prediction value in es
    task_detail = es_prediction.get(index=index_manage_prediction_task, \
            doc_type=type_manage_prediction_task, id=origin_task_name)["_source"]
    if current_ts >= int(task_detail["stop_time"]):
        task_detail["finish"] = "1"
        task_detail["processing_status"] = "0"

        # update task info
        es_prediction.index(index=index_manage_prediction_task, \
            doc_type=type_manage_prediction_task, id=origin_task_name, body=task_detail)

    # update prediction
    es_prediction.update(index=task_name, doc_type=index_type_micro_task, id=current_ts, body={"doc":{"prediction_value": prediction_value}})

    return True

if __name__ == "__main__":
    organize()


