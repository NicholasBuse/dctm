#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#

from dctmpy import *
from dctmpy.obj.entrypoints import EntryPoints
from dctmpy.obj.typedobject import TypedObject
from dctmpy.type.attrvalue import AttrValue


def requestDocbaseMap(handle, version):
    obj = TypedObject(serializationVersion=0)
    obj.add(AttrValue(name="DBR_REQUEST_NAME", type=STRING, values=["DBRN_GET_DOCBASE_MAP"]))
    obj.add(AttrValue(name="DBR_REQUEST_VERSION", type=INT, values=[1]))
    obj.add(AttrValue(name="DBR_REQUEST_HANDLE", type=STRING, values=[handle]))
    obj.add(AttrValue(name="DBR_SOFTWARE_VERSION", type=STRING, values=[version]))
    return obj.serialize()


def requestServerMap(handle, version, docbase):
    obj = TypedObject(serializationVersion=0)
    obj.add(AttrValue(name="r_docbase_name", type=STRING, values=[docbase]))
    obj.add(AttrValue(name="r_map_name", type=STRING, values=["mn_cs_map"]))
    obj.add(AttrValue(name="DBR_REQUEST_NAME", type=STRING, values=["DBRN_GET_SERVER_MAP"]))
    obj.add(AttrValue(name="DBR_REQUEST_VERSION", type=INT, values=[1]))
    obj.add(AttrValue(name="DBR_REQUEST_HANDLE", type=STRING, values=[handle]))
    obj.add(AttrValue(name="DBR_SOFTWARE_VERSION", type=STRING, values=[version]))
    return obj.serialize()


def requestEntryPoints(session):
    obj = EntryPoints(session=session)
    obj.add(AttrValue(name="LANGUAGE", type=INT, values=[getLocaleId()]))
    obj.add(AttrValue(name="CHARACTER_SET", type=INT, values=[getCharsetId()]))
    obj.add(AttrValue(name="PLATFORM_ENUM", type=INT, values=[getPlatformId()]))
    obj.add(AttrValue(name="PLATFORM_VERSION_IMAGE", type=STRING, values=["python"]))
    obj.add(AttrValue(name="UTC_OFFSET", type=INT, values=[getOffsetInSeconds()]))
    obj.add(AttrValue(name="SDF_AN_custom_date_order", type=INT, values=[0]))
    obj.add(AttrValue(name="SDF_AN_custom_scan_fields", type=INT, values=[0]))
    obj.add(AttrValue(name="SDF_AN_date_separator", type=STRING, values=["/"]))
    obj.add(AttrValue(name="SDF_AN_date_order", type=INT, values=[2]))
    obj.add(AttrValue(name="SDF_AN_day_leading_zero", type=BOOL, values=[True]))
    obj.add(AttrValue(name="SDF_AN_month_leading_zero", type=BOOL, values=[True]))
    obj.add(AttrValue(name="SDF_AN_century", type=BOOL, values=[True]))
    obj.add(AttrValue(name="SDF_AN_time_separator", type=STRING, values=[":"]))
    obj.add(AttrValue(name="SDF_AN_hours_24", type=BOOL, values=[True]))
    obj.add(AttrValue(name="SDF_AN_hour_leading_zero", type=BOOL, values=[True]))
    obj.add(AttrValue(name="SDF_AN_noon_is_zero", type=BOOL, values=[False]))
    obj.add(AttrValue(name="SDF_AN_am", type=STRING, values=["AM"]))
    obj.add(AttrValue(name="SDF_AN_pm", type=STRING, values=["PM"]))
    obj.add(AttrValue(name="PLATFORM_EXTRA", type=INT, repeating=True, values=[0, 0, 0, 0]))
    obj.add(AttrValue(name="APPLICATION_CODE", type=STRING, values=[""]))
    return obj.serialize()


def requestAuthenticate(session, username, password):
    obj = TypedObject(session=session)
    obj.add(AttrValue(name="CONNECT_POOLING", type=BOOL, values=[False]))
    obj.add(AttrValue(name="USER_PASSWORD", type=STRING, values=[password]))
    obj.add(AttrValue(name="AUTHENTICATION_ONLY", type=BOOL, values=[False]))
    obj.add(AttrValue(name="CHECK_ONLY", type=BOOL, values=[False]))
    obj.add(AttrValue(name="LOGON_NAME", type=STRING, values=[username]))
    return obj.serialize()


def requestServerConfig(session):
    obj = TypedObject(session=session)
    obj.add(AttrValue(name="OBJECT_TYPE", type=STRING, values=["dm_server_config"]))
    obj.add(AttrValue(name="FOR_REVERT", type=BOOL, values=["F"]))
    obj.add(AttrValue(name="CACHE_VSTAMP", type=INT, values=[0]))
    return obj.serialize()


def requestDocbaseConfig(session):
    obj = TypedObject(session=session)
    obj.add(AttrValue(name="OBJECT_TYPE", type=STRING, values=["dm_docbase_config"]))
    obj.add(AttrValue(name="FOR_REVERT", type=BOOL, values=["F"]))
    obj.add(AttrValue(name="CACHE_VSTAMP", type=INT, values=[0]))
    return obj.serialize()


def requestFetchType(session, typename, vstamp):
    obj = TypedObject(session=session)
    obj.add(AttrValue(name="TYPE_NAME", type=STRING, values=[typename]))
    obj.add(AttrValue(name="CACHE_VSTAMP", type=INT, values=[vstamp]))
    return obj.serialize()


def requestGetErrors(session):
    obj = TypedObject(session=session)
    obj.add(AttrValue(name="OBJECT_TYPE", type=STRING, values=["dmError"]))
    return obj.serialize()


def requestQuery(session, query, forUpdate, batchHint, bofDql):
    obj = TypedObject(session=session)
    obj.add(AttrValue(name="QUERY", type=STRING, values=[query]))
    obj.add(AttrValue(name="FOR_UPDATE", type=BOOL, values=[forUpdate]))
    obj.add(AttrValue(name="BATCH_HINT", type=INT, values=[batchHint]))
    obj.add(AttrValue(name="BOF_DQL", type=BOOL, values=[bofDql]))
    return obj.serialize()
