"""
数据源管理 API
提供 Excel 和 HTTP API 数据源的访问接口
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging
from pathlib import Path

from app.core.mcp.tools.excel import ExcelTool
from app.core.mcp.tools.api_datasource import APIDatasourceTool
from app.dependencies import get_excel_tool, get_api_tool

logger = logging.getLogger(__name__)

router = APIRouter()


# ============== Request/Response Models ==============

class ExcelQueryRequest(BaseModel):
    """Excel 查询请求"""
    file_path: str
    sheet_name: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    columns: Optional[List[str]] = None
    limit: int = Field(default=1000, ge=1, le=10000)


class ExcelWriteRequest(BaseModel):
    """Excel 写入请求"""
    file_path: str
    data: List[Dict[str, Any]]
    sheet_name: str = "Sheet1"
    mode: str = Field(default="overwrite", pattern="^(overwrite|append)$")


class APICallRequest(BaseModel):
    """API 调用请求"""
    api_name: str
    endpoint: str
    method: str = "GET"
    params: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None


class APIRegistrationRequest(BaseModel):
    """API 注册请求"""
    name: str
    base_url: str
    auth_type: Optional[str] = None
    auth_value: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


# ============== Excel Endpoints ==============

@router.post("/excel/query")
async def query_excel(
    request: ExcelQueryRequest,
    excel_tool: ExcelTool = Depends(get_excel_tool)
):
    """
    查询 Excel 数据

    支持按列筛选、指定工作表、限制行数等操作。

    **示例请求：**
    ```json
    {
      "file_path": "sales_data.xlsx",
      "sheet_name": "2024-01",
      "filters": {"region": "华东"},
      "columns": ["date", "product", "sales"],
      "limit": 100
    }
    ```
    """
    if request.filters:
        result = await excel_tool.query_excel(
            file_path=request.file_path,
            filters=request.filters,
            sheet_name=request.sheet_name
        )
    else:
        result = await excel_tool.read_excel(
            file_path=request.file_path,
            sheet_name=request.sheet_name,
            columns=request.columns,
            limit=request.limit
        )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return result.data


@router.post("/excel/write")
async def write_excel(
    request: ExcelWriteRequest,
    excel_tool: ExcelTool = Depends(get_excel_tool)
):
    """
    写入 Excel 数据

    支持覆盖或追加模式。

    **示例请求：**
    ```json
    {
      "file_path": "report.xlsx",
      "data": [
        {"date": "2024-01-01", "sales": 1000, "region": "华东"}
      ],
      "sheet_name": "Sheet1",
      "mode": "overwrite"
    }
    ```
    """
    result = await excel_tool.write_excel(
        file_path=request.file_path,
        data=request.data,
        sheet_name=request.sheet_name,
        mode=request.mode
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return result.data


@router.get("/excel/info/{file_path:path}")
async def get_excel_info(
    file_path: str,
    excel_tool: ExcelTool = Depends(get_excel_tool)
):
    """获取 Excel 文件信息（工作表、列等）"""
    result = await excel_tool.get_file_info(file_path)

    if not result.success:
        raise HTTPException(status_code=404, detail=result.error)

    return result.data


@router.get("/excel/download/{filename}")
async def download_excel(
    filename: str,
    excel_tool: ExcelTool = Depends(get_excel_tool)
):
    """下载 Excel 文件"""
    file_path = excel_tool.base_path / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@router.post("/excel/upload")
async def upload_excel(
    file: UploadFile = File(...),
    excel_tool: ExcelTool = Depends(get_excel_tool)
):
    """
    上传 Excel 文件

    保存到服务器的 data/excel 目录。
    """
    try:
        file_path = excel_tool.base_path / file.filename

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        return {
            "success": True,
            "filename": file.filename,
            "file_path": str(file_path),
            "size": len(content)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== API Datasource Endpoints ==============

@router.post("/api/call")
async def call_api(
    request: APICallRequest,
    api_tool: APIDatasourceTool = Depends(get_api_tool)
):
    """
    调用已注册的 API

    **示例请求：**
    ```json
    {
      "api_name": "weather",
      "endpoint": "/current?city=Beijing",
      "method": "GET"
    }
    ```
    """
    result = await api_tool.call_api(
        api_name=request.api_name,
        endpoint=request.endpoint,
        method=request.method,
        params=request.params,
        data=request.data
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return result.data


@router.post("/api/register")
async def register_api(
    request: APIRegistrationRequest,
    api_tool: APIDatasourceTool = Depends(get_api_tool)
):
    """
    注册新的 API 数据源

    **示例请求：**
    ```json
    {
      "name": "my_api",
      "base_url": "https://api.example.com/v1",
      "auth_type": "bearer",
      "auth_value": "my_token",
      "headers": {"User-Agent": "MyAgent"}
    }
    ```
    """
    api_tool.register_api(
        name=request.name,
        base_url=request.base_url,
        auth_type=request.auth_type,
        auth_value=request.auth_value,
        headers=request.headers
    )

    return {
        "success": True,
        "message": f"API {request.name} 注册成功"
    }


@router.get("/api/list")
async def list_apis(
    api_tool: APIDatasourceTool = Depends(get_api_tool)
):
    """列出所有已注册的 API"""
    return {
        "apis": [
            {
                "name": name,
                "base_url": config["base_url"],
                "auth_type": config.get("auth_type")
            }
            for name, config in api_tool.api_configs.items()
        ]
    }


@router.delete("/api/{api_name}")
async def delete_api(
    api_name: str,
    api_tool: APIDatasourceTool = Depends(get_api_tool)
):
    """删除已注册的 API"""
    if api_name in api_tool.api_configs:
        del api_tool.api_configs[api_name]
        return {"success": True, "message": f"API {api_name} 已删除"}
    else:
        raise HTTPException(status_code=404, detail="API 不存在")
