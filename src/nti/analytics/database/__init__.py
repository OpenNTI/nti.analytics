__import__('pkg_resources').declare_namespace(__name__)

from zope import component

from sqlalchemy import String
from sqlalchemy import BigInteger
from sqlalchemy.ext.declarative import declarative_base

from nti.analytics.database.interfaces import IAnalyticsDB

Base = declarative_base()

SESSION_COLUMN_TYPE = String( 64 )
NTIID_COLUMN_TYPE = String( 256 )
INTID_COLUMN_TYPE = BigInteger

def get_analytics_db():
	return component.getUtility( IAnalyticsDB )

