"""
PDF解析服务 - 使用Marker将PDF转换为Markdown
"""
import asyncio
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any
import httpx
import structlog

logger = structlog.get_logger(__name__)


class PDFParser:
    """PDF解析器（使用Marker）"""
    
    def __init__(self):
        self._marker_available = None
    
    def _check_marker(self) -> bool:
        """检查marker是否可用"""
        if self._marker_available is None:
            try:
                from marker.converters.pdf import PdfConverter
                self._marker_available = True
            except ImportError:
                logger.warning("Marker not installed. PDF parsing disabled.")
                self._marker_available = False
        return self._marker_available
    
    async def download_pdf(self, url: str, output_path: Path) -> bool:
        """下载PDF文件"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                logger.info("PDF downloaded", url=url, size=len(response.content))
                return True
        except Exception as e:
            logger.error("PDF download failed", url=url, error=str(e))
            return False
    
    async def parse_pdf(self, pdf_path: Path) -> Optional[str]:
        """
        解析PDF为Markdown
        
        Args:
            pdf_path: PDF文件路径
        
        Returns:
            Markdown文本，失败返回None
        """
        if not self._check_marker():
            return None
        
        try:
            # Marker是CPU密集型，在线程池中运行
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._parse_sync, pdf_path
            )
            return result
        except Exception as e:
            logger.error("PDF parse failed", path=str(pdf_path), error=str(e))
            return None
    
    def _parse_sync(self, pdf_path: Path) -> str:
        """同步解析PDF"""
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        
        # 创建模型（首次调用会下载模型）
        model_dict = create_model_dict()
        converter = PdfConverter(artifact_dict=model_dict)
        
        # 转换
        result = converter(str(pdf_path))
        
        # 返回Markdown文本
        return result.markdown
    
    async def parse_from_url(self, url: str) -> Optional[str]:
        """
        从URL下载并解析PDF
        
        Args:
            url: PDF URL
        
        Returns:
            Markdown文本
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "paper.pdf"
            
            if not await self.download_pdf(url, pdf_path):
                return None
            
            return await self.parse_pdf(pdf_path)
    
    async def extract_figures_from_url(
        self, 
        url: str, 
        max_figures: int = 5
    ) -> List[Dict[str, Any]]:
        """
        从PDF URL提取图表为base64图像（用于VL模型）
        
        Args:
            url: PDF URL
            max_figures: 最大提取图表数量
        
        Returns:
            图表列表 [{"page": 1, "index": 0, "base64": "...", "ext": "png"}]
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.warning("PyMuPDF not installed, figure extraction disabled")
            return []
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                doc = fitz.open(stream=response.content, filetype="pdf")
                figures = []
                
                for page_num in range(len(doc)):
                    if len(figures) >= max_figures:
                        break
                    
                    page = doc[page_num]
                    images = page.get_images()
                    
                    for img_index, img in enumerate(images):
                        if len(figures) >= max_figures:
                            break
                        
                        xref = img[0]
                        try:
                            base_image = doc.extract_image(xref)
                            image_bytes = base_image["image"]
                            
                            # 跳过太小的图片（可能是图标）
                            if len(image_bytes) < 5000:
                                continue
                            
                            import base64
                            b64 = base64.b64encode(image_bytes).decode()
                            
                            figures.append({
                                "page": page_num + 1,
                                "index": img_index,
                                "base64": b64,
                                "ext": base_image.get("ext", "png"),
                                "size": len(image_bytes)
                            })
                        except Exception as e:
                            logger.debug(f"Skip image extraction: {e}")
                            continue
                
                doc.close()
                logger.info(f"Extracted {len(figures)} figures from PDF")
                return figures
                
        except Exception as e:
            logger.error("Figure extraction failed", error=str(e))
            return []


# 降级方案：仅提取文本（不使用Marker）
class SimplePDFParser:
    """简单PDF解析器（降级方案）"""
    
    async def parse_from_url(self, url: str) -> Optional[str]:
        """使用PyMuPDF提取纯文本"""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.warning("PyMuPDF not installed")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # 直接从内存读取
                doc = fitz.open(stream=response.content, filetype="pdf")
                text_parts = []
                
                for page in doc:
                    text_parts.append(page.get_text())
                
                doc.close()
                return "\n\n".join(text_parts)
        except Exception as e:
            logger.error("Simple PDF parse failed", error=str(e))
            return None


# 工厂函数
def get_pdf_parser() -> PDFParser:
    """获取PDF解析器实例"""
    return PDFParser()


def get_simple_parser() -> SimplePDFParser:
    """获取简单解析器（降级方案）"""
    return SimplePDFParser()
