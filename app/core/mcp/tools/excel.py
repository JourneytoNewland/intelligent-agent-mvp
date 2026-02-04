"""
Excel MCP 工具
支持从 Excel 文件读取数据和写入报表
"""

import os
import pandas as pd
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging
from datetime import datetime
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ToolResult(BaseModel):
    """工具执行结果"""
    success: bool = Field(..., description="执行是否成功")
    data: Optional[Any] = Field(default=None, description="返回数据")
    message: Optional[str] = Field(default=None, description="执行消息")
    error: Optional[str] = Field(default=None, description="错误信息")


class ExcelTool:
    """
    Excel 数据操作工具

    功能：
    1. 读取 Excel 文件数据
    2. 查询和筛选数据
    3. 将数据写入 Excel 文件
    4. 支持多种格式（.xlsx, .xls, .csv）
    """

    name = "excel"
    description = "读取和写入 Excel 文件数据"

    def __init__(self, base_path: str = "./data/excel"):
        # super().__init__()
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def read_excel(
        self,
        file_path: str,
        sheet_name: Optional[str] = None,
        range_filter: Optional[str] = None,
        columns: Optional[List[str]] = None,
        limit: int = 1000
    ) -> ToolResult:
        """
        读取 Excel 文件

        Args:
            file_path: 文件路径（相对于 base_path）
            sheet_name: 工作表名称（默认第一个）
            range_filter: 数据范围（如 "A1:Z100"）
            columns: 要读取的列（默认全部）
            limit: 最大行数

        Returns:
            ToolResult: 包含数据和元信息
        """
        try:
            full_path = self.base_path / file_path

            if not full_path.exists():
                return ToolResult(
                    success=False,
                    error=f"文件不存在: {full_path}"
                )

            # 读取 Excel
            df = pd.read_excel(
                full_path,
                sheet_name=sheet_name,
                usecols=columns,
                nrows=limit
            )

            # 处理 range_filter（简化实现）
            if range_filter:
                # TODO: 实现 Excel 范围解析
                logger.warning(f"范围筛选暂未实现: {range_filter}")

            # 转换为字典列表
            data = df.to_dict(orient="records")

            return ToolResult(
                success=True,
                data={
                    "file_path": file_path,
                    "sheet_name": sheet_name or "Sheet1",
                    "rows": len(data),
                    "columns": list(df.columns),
                    "data": data
                },
                message=f"成功读取 {len(data)} 行数据"
            )

        except Exception as e:
            logger.error(f"读取 Excel 失败: {e}")
            return ToolResult(
                success=False,
                error=str(e)
            )

    async def write_excel(
        self,
        file_path: str,
        data: List[Dict[str, Any]],
        sheet_name: str = "Sheet1",
        mode: str = "overwrite"
    ) -> ToolResult:
        """
        写入 Excel 文件

        Args:
            file_path: 文件路径（相对于 base_path）
            data: 数据列表
            sheet_name: 工作表名称
            mode: 写入模式（overwrite/append）

        Returns:
            ToolResult: 写入结果
        """
        try:
            full_path = self.base_path / file_path

            # 确保目录存在
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # 转换为 DataFrame
            df = pd.DataFrame(data)

            # 写入模式
            if mode == "append" and full_path.exists():
                # 追加模式：读取现有数据并合并
                existing_df = pd.read_excel(full_path, sheet_name=sheet_name)
                df = pd.concat([existing_df, df], ignore_index=True)

            # 写入 Excel
            df.to_excel(
                full_path,
                sheet_name=sheet_name,
                index=False,
                engine='openpyxl'
            )

            return ToolResult(
                success=True,
                data={
                    "file_path": file_path,
                    "sheet_name": sheet_name,
                    "rows_written": len(df),
                    "mode": mode
                },
                message=f"成功写入 {len(df)} 行数据到 {file_path}"
            )

        except Exception as e:
            logger.error(f"写入 Excel 失败: {e}")
            return ToolResult(
                success=False,
                error=str(e)
            )

    async def query_excel(
        self,
        file_path: str,
        filters: Dict[str, Any],
        sheet_name: Optional[str] = None
    ) -> ToolResult:
        """
        查询 Excel 数据（带筛选）

        Args:
            file_path: 文件路径
            filters: 筛选条件，如 {"column": "value"}
            sheet_name: 工作表名称

        Returns:
            ToolResult: 筛选后的数据
        """
        try:
            full_path = self.base_path / file_path

            if not full_path.exists():
                return ToolResult(
                    success=False,
                    error=f"文件不存在: {full_path}"
                )

            # 读取数据
            df = pd.read_excel(full_path, sheet_name=sheet_name)

            # 应用筛选
            for column, value in filters.items():
                if column in df.columns:
                    df = df[df[column] == value]
                else:
                    logger.warning(f"列不存在: {column}")

            # 转换为字典列表
            data = df.to_dict(orient="records")

            return ToolResult(
                success=True,
                data={
                    "file_path": file_path,
                    "filters": filters,
                    "rows": len(data),
                    "data": data
                },
                message=f"查询到 {len(data)} 行匹配数据"
            )

        except Exception as e:
            logger.error(f"查询 Excel 失败: {e}")
            return ToolResult(
                success=False,
                error=str(e)
            )

    async def export_to_excel(
        self,
        data: List[Dict[str, Any]],
        filename: Optional[str] = None,
        sheet_name: str = "Report"
    ) -> ToolResult:
        """
        导出数据到 Excel（自动生成文件名）

        Args:
            data: 要导出的数据
            filename: 文件名（不指定则自动生成）
            sheet_name: 工作表名称

        Returns:
            ToolResult: 导出结果和文件路径
        """
        try:
            if not filename:
                # 自动生成文件名：report_YYYYMMDD_HHMMSS.xlsx
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"report_{timestamp}.xlsx"

            full_path = self.base_path / filename

            # 写入数据
            result = await self.write_excel(
                file_path=filename,
                data=data,
                sheet_name=sheet_name,
                mode="overwrite"
            )

            if result.success:
                result.data["download_url"] = f"/api/v1/datasources/excel/download/{filename}"

            return result

        except Exception as e:
            logger.error(f"导出 Excel 失败: {e}")
            return ToolResult(
                success=False,
                error=str(e)
            )

    async def get_file_info(self, file_path: str) -> ToolResult:
        """
        获取 Excel 文件信息

        Args:
            file_path: 文件路径

        Returns:
            ToolResult: 文件元信息
        """
        try:
            full_path = self.base_path / file_path

            if not full_path.exists():
                return ToolResult(
                    success=False,
                    error=f"文件不存在: {full_path}"
                )

            # 读取 Excel 文件信息
            excel_file = pd.ExcelFile(full_path)
            sheet_names = excel_file.sheet_names

            sheet_info = {}
            for sheet in sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet, nrows=0)
                sheet_info[sheet] = {
                    "columns": list(df.columns),
                    "column_count": len(df.columns)
                }

            return ToolResult(
                success=True,
                data={
                    "file_path": file_path,
                    "file_size": full_path.stat().st_size,
                    "sheet_names": sheet_names,
                    "sheets": sheet_info
                }
            )

        except Exception as e:
            logger.error(f"获取文件信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e)
            )
