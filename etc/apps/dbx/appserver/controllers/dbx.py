import logging
from splunk.appserver.mrsparkle.lib.decorators import expose_page
import splunk.appserver.mrsparkle.controllers as controllers
from spp.java.bridge import executeBridgeCommand

logger = logging.getLogger("dbx.controllers.dbinfo")
logger.setLevel(logging.DEBUG)

class DBXController(controllers.BaseController):
	@expose_page(must_login=True)
	def status(self, **kwargs):
		ret, out, err = executeBridgeCommand("com.splunk.bridge.stats.SystemStatus", [], fetchOutput=True)
		return out