# -*- coding: utf-8 -*-
# created by restran on 2016/03/06
from __future__ import unicode_literals

import json

from bson import SON
from django.views.decorators.http import require_http_methods

from django.views.decorators.csrf import csrf_protect

from common.utils import http_response_json
from accounts.decorators import login_required
import logging
from ..models import AccessHourCounter, AccessTotalDayCounter, \
    query_access_count, AccessDayCounter, Client, Endpoint
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def get_count_by_query(request):
    """
    获取访问统计
    :param request:
    :return:
    """
    success, msg, data = False, '', []
    now = datetime.now()
    post_data = json.loads(request.body)
    logger.debug(post_data)
    if post_data['begin_time'] != '' and post_data['begin_time'] is not None:
        post_data['begin_time'] = datetime.strptime(post_data['begin_time'], '%Y-%m-%d %H:%M')
    else:
        post_data['begin_time'] = None

    if post_data['end_time'] != '' and post_data['end_time'] is not None:
        post_data['end_time'] = datetime.strptime(post_data['end_time'], '%Y-%m-%d %H:%M')
    else:
        post_data['end_time'] = None

    by_search = post_data.get('by_search', False)
    time_frame = post_data.get('time_frame', None)
    if not by_search:
        post_data['require_total'] = True

    if post_data['begin_time'] is None:
        if post_data['end_time'] is None:
            base_time = datetime.now()
        else:
            base_time = post_data['end_time']
    else:
        base_time = None

    if base_time is not None and time_frame is not None:
        if time_frame == '24h':
            post_data['begin_time'] = datetime(base_time.year, base_time.month, base_time.day, base_time.hour) \
                                      - timedelta(hours=23)
            post_data['x_data_use_hour'] = True
        elif time_frame == '7d':
            post_data['begin_time'] = datetime(base_time.year, base_time.month, base_time.day) \
                                      - timedelta(days=6)
        elif time_frame == '30d':
            post_data['begin_time'] = datetime(base_time.year, base_time.month, base_time.day) \
                                      - timedelta(days=29)
        elif time_frame == '1d':
            post_data['begin_time'] = datetime(base_time.year, base_time.month, base_time.day)
            post_data['end_time'] = post_data['begin_time'] + timedelta(days=1) - timedelta(seconds=1)
            post_data['x_data_use_hour'] = True
        elif time_frame == '1m':
            post_data['begin_time'] = datetime(base_time.year, base_time.month, 1)
            post_data['end_time'] = post_data['begin_time'] + relativedelta(months=1) - timedelta(seconds=1)

    if post_data['begin_time'] is None:
        post_data['begin_time'] = datetime(now.year, now.month, now.day, now.hour) \
                                  - timedelta(hours=24)

    if post_data['end_time'] is None:
        end_time = datetime.now()
    else:
        end_time = post_data['end_time']

    if post_data['begin_time'] + timedelta(hours=36) > end_time:
        post_data['time_unit'] = 'hour'
    else:
        post_data['time_unit'] = 'day'

    x_data, y_data = query_access_count(**post_data)
    data = {
        'x_data': x_data,
        'y_data': y_data
    }

    return http_response_json({'success': True, 'msg': msg, 'data': data})


@login_required
@csrf_protect
@require_http_methods(["GET"])
def get_total_count(request):
    """
    获取累计访问统计
    :param request:
    :return:
    """
    success, msg, data = False, '', []
    # post_data = json.loads(request.body)
    total_count = AccessTotalDayCounter.objects().aggregate_sum('count')
    data = {'total_count': total_count}
    return http_response_json({'success': True, 'msg': msg, 'data': data})


def parse_ratio_post_data(post_data):
    now = datetime.now()
    logger.debug(post_data)
    if post_data['begin_time'] != '' and post_data['begin_time'] is not None:
        post_data['begin_time'] = datetime.strptime(post_data['begin_time'], '%Y-%m-%d')
    else:
        post_data['begin_time'] = None

    if post_data['end_time'] != '' and post_data['end_time'] is not None:
        post_data['end_time'] = datetime.strptime(post_data['end_time'], '%Y-%m-%d')
    else:
        post_data['end_time'] = None

    time_frame = post_data.get('time_frame', None)

    if post_data['begin_time'] is None:
        if post_data['end_time'] is None:
            base_time = datetime.now()
        else:
            base_time = post_data['end_time']
    else:
        base_time = None

    time_unit = 'day'
    if base_time is not None and time_frame is not None:
        if time_frame == '24h':
            post_data['begin_time'] = datetime(base_time.year, base_time.month, base_time.day, base_time.hour) \
                                      - timedelta(hours=23)
            time_unit = 'hour'
        elif time_frame == '7d':
            post_data['begin_time'] = datetime(base_time.year, base_time.month, base_time.day) \
                                      - timedelta(days=6)
        elif time_frame == '30d':
            post_data['begin_time'] = datetime(base_time.year, base_time.month, base_time.day) \
                                      - timedelta(days=29)
        elif time_frame == '1d':
            post_data['begin_time'] = datetime(base_time.year, base_time.month, base_time.day)
            post_data['end_time'] = post_data['begin_time'] + timedelta(days=1) - timedelta(seconds=1)
            post_data['x_data_use_hour'] = True
        elif time_frame == '1m':
            post_data['begin_time'] = datetime(base_time.year, base_time.month, 1)
            post_data['end_time'] = post_data['begin_time'] + relativedelta(months=1) - timedelta(seconds=1)

    if post_data['begin_time'] is None:
        post_data['begin_time'] = datetime(now.year, now.month, now.day, now.hour) \
                                  - timedelta(hours=24)

    filter_dict = {}

    if time_unit == 'hour':
        model_cls = AccessHourCounter
    else:
        model_cls = AccessDayCounter

    if post_data['begin_time']:
        filter_dict['date__gte'] = post_data['begin_time']
    if post_data['end_time']:
        filter_dict['date__lte'] = post_data['end_time']

    return model_cls, filter_dict


@login_required
@csrf_protect
@require_http_methods(["POST"])
def get_client_ratio(request):
    """
    获取今天 client 访问占比
    :param request:
    :return:
    """
    success, msg, data = False, '', []
    post_data = json.loads(request.body)
    model_cls, filter_dict = parse_ratio_post_data(post_data)
    pipeline = [
        {
            "$group": {
                "_id": "$client_id",
                "count": {"$sum": "$count"}
            },
        },
        {
            "$sort": SON([("count", -1), ("_id", -1)])
        }
    ]

    count_list = model_cls.objects(**filter_dict).aggregate(*pipeline)
    count_list = list(count_list)
    client_id_list = [t['_id'] for t in count_list]
    clients = Client.objects.filter(id__in=client_id_list).values('name', 'id')
    client_dict = {}
    for t in clients:
        client_dict[t['id']] = t['name']

    legend = []
    y_data = []
    for t in count_list:
        name = client_dict.get(t['_id'])
        if name:
            legend.append(name)
            y_data.append({'value': t['count'], 'name': name})

    data = {
        'legend': legend,
        'y_data': y_data
    }
    return http_response_json({'success': True, 'msg': msg, 'data': data})


@login_required
@csrf_protect
@require_http_methods(["POST"])
def get_endpoint_ratio(request):
    """
    获取今天 endpoint 访问占比
    :param request:
    :return:
    """
    success, msg, data = False, '', []
    post_data = json.loads(request.body)
    model_cls, filter_dict = parse_ratio_post_data(post_data)

    pipeline = [
        {
            "$group": {
                "_id": "$endpoint_id",
                "count": {"$sum": "$count"}
            },
        },
        {
            "$sort": SON([("count", -1), ("_id", -1)])
        }
    ]

    count_list = model_cls.objects(**filter_dict).aggregate(*pipeline)
    count_list = list(count_list)
    endpoint_id_list = [t['_id'] for t in count_list]
    endpoints = Endpoint.objects.filter(id__in=endpoint_id_list).values('unique_name', 'id')
    client_dict = {}
    for t in endpoints:
        client_dict[t['id']] = t['unique_name']

    legend = []
    y_data = []
    for t in count_list:
        name = client_dict.get(t['_id'])
        if name:
            legend.append(name)
            y_data.append({'value': t['count'], 'name': name})

    data = {
        'legend': legend,
        'y_data': y_data
    }
    return http_response_json({'success': True, 'msg': msg, 'data': data})
