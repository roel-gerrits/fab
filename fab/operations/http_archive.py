from ..data.base import PathObj, String
from .decorator import operation
from .http_get import http_get
from .extract import extract

from ..building import Context


@operation
async def http_archive(context: Context, url: String) -> PathObj:
    archive = await http_get.execute(context, args=[url], kwargs={})
    contents = await extract.execute(context, args=[archive], kwargs={})
    assert isinstance(contents, PathObj)
    return contents
