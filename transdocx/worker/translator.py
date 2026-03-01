import json
import asyncio
import os
from transdocx.document.document import RunInfo, TextSegment, TableCellSegment, ChartSegment, SmartArtSegment
from transdocx.utils.decorator import timer, log_errors
from transdocx.utils.prompt_builder import PromptBuilder
import logging
import re
from collections import defaultdict
from tqdm import tqdm

logging.basicConfig(level=logging.WARNING)

class Translator:
    """Dịch nội dung từ checkpoint file hỗ trợ cả OpenAI API và MarianMT local"""
    
    def __init__(self, checkpoint_file: str, client, engine: str = "openai", model: str = "gpt-4o-mini", source_lang: str = "English", target_lang: str = "Vietnamese", max_chunk_size: int = 5000, max_concurrent: int = 100):
        self.checkpoint_file = checkpoint_file
        self.client = client
        self.engine = engine
        self.model = model
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.max_chunk_size = max_chunk_size
        self.max_concurrent = max_concurrent
        
        if self.engine == "openai":
            self.prompt_builder = PromptBuilder(self.source_lang, self.target_lang)
            
        self.logger = logging.getLogger(self.__class__.__name__)
        self.semaphore = asyncio.Semaphore(self.max_concurrent)

    # =========================================================================
    # CÁC HÀM TIỆN ÍCH CHO MARIANMT (DỊCH NGUYÊN ĐOẠN ĐỂ GIỮ NGỮ CẢNH)
    # =========================================================================
    async def _marian_translate_segment_runs(self, items: list):
        """Gộp text của tất cả các run trong 1 segment thành 1 câu hoàn chỉnh để dịch"""
        tasks = []
        for item in items:
            # Gộp toàn bộ text của đoạn văn
            full_text = "".join([run['text'] for run in item['runs_list']])
            if full_text.strip():
                tasks.append(self._marian_translate_full_text(item, full_text))
            else:
                for run in item['runs_list']:
                    run['translated_text'] = run['text']
        
        if tasks:
            await asyncio.gather(*tasks)

    async def _marian_translate_full_text(self, item: dict, full_text: str):
        """Thực hiện dịch và dồn kết quả vào Run đầu tiên, ẩn các Run sau"""
        async with self.semaphore:
            try:
                translated = await self.client.translate_text(full_text)
                if item['runs_list']:
                    # Dồn bản dịch vào Run 0
                    item['runs_list'][0]['translated_text'] = translated
                    # Xóa text các Run phía sau để không bị lặp chữ
                    for i in range(1, len(item['runs_list'])):
                        item['runs_list'][i]['translated_text'] = ""
            except Exception as e:
                self.logger.error(f"Marian translation error: {e}")
                for run in item['runs_list']:
                    run['translated_text'] = run['text']

    async def _marian_process_texts(self, items: list):
        """Dịch trực tiếp trường 'text' (Dành cho Chart/SmartArt)"""
        async def _translate_single(item):
            async with self.semaphore:
                try:
                    item['translated_text'] = await self.client.translate_text(item['text'])
                except Exception:
                    item['translated_text'] = item['text']
                    
        tasks = [_translate_single(item) for item in items if item['text'].strip()]
        for item in items:
            if not item['text'].strip():
                item['translated_text'] = item['text']
        if tasks:
            await asyncio.gather(*tasks)

    # =========================================================================
    # CÁC HÀM TIỆN ÍCH CHO OPENAI (GIỮ NGUYÊN)
    # =========================================================================
    async def _translate_text(self, text: str, context: str = "general") -> str:
        async with self.semaphore:
            try:
                if self.engine == "marian":
                    return await self.client.translate_text(text)
                    
                messages = self.prompt_builder.build_messages(text)
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                self.logger.error(f"   ⚠️  Translation error: {e}")
                return text

    def _chunk_text_segments(self, text_segments: list[TextSegment]) -> list[list[TextSegment]]:
        chunks = []
        current_chunk = []
        current_size = 0
        for segment in text_segments:
            segment_size = len(segment['full_text'])
            if current_size + segment_size > self.max_chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_size = 0
            current_chunk.append(segment)
            current_size += segment_size
        if current_chunk:
            chunks.append(current_chunk)
        return chunks
    
    def _create_marked_text_from_runs(self, runs_list: list[RunInfo], prefix: str, idx: str) -> tuple[str, list[int]]:
        marked_parts = []
        translatable_indices = []
        marker_idx = 0
        for run_idx, run in enumerate(runs_list):
            text = run['text']
            if text.strip():
                marked_parts.append(f"<R{marker_idx}>{text}</R{marker_idx}>")
                translatable_indices.append(run_idx)
                marker_idx += 1
            else:
                marked_parts.append(text)
        return "".join(marked_parts), translatable_indices
    
    def _extract_translated_runs(self, translated_text: str, runs_list: list[RunInfo], translatable_indices: list[int], prefix: str, idx: str) -> bool:
        success = True
        for marker_idx, run_idx in enumerate(translatable_indices):
            run = runs_list[run_idx]
            pattern = f"<R{marker_idx}>(.*?)</R{marker_idx}>"
            match = re.search(pattern, translated_text, re.DOTALL)
            if match:
                run['translated_text'] = match.group(1)
            else:
                self.logger.warning(f"   ⚠️  Marker <R{marker_idx}> not found in {prefix}-{idx}, keeping original text")
                run['translated_text'] = run['text']
                success = False
        for run_idx, run in enumerate(runs_list):
            if run_idx not in translatable_indices:
                run['translated_text'] = run['text']
        return success

    # =========================================================================
    # CORE TRANSLATION LOGIC (RẼ NHÁNH CHO 2 ENGINE)
    # =========================================================================
    async def _translate_text_chunk(self, chunk: list[TextSegment], progress_callback=None) -> list[TextSegment]:
        if self.engine == "marian":
            await self._marian_translate_segment_runs(chunk)
            for segment in chunk:
                segment['full_text'] = "".join(run.get('translated_text', run['text']) for run in segment['runs_list'])
            if progress_callback: progress_callback()
            return chunk

        marked_segments = []
        segment_translatable_map = {}
        for segment in chunk:
            seg_idx = segment['seg_idx']
            marked_text, translatable_indices = self._create_marked_text_from_runs(segment['runs_list'], 'seg', seg_idx)
            segment_translatable_map[seg_idx] = translatable_indices
            marked_segments.append(f"<SEG{seg_idx}>\n{marked_text}\n</SEG{seg_idx}>")
        
        combined_text = "\n\n".join(marked_segments)
        translated_combined = await self._translate_text(combined_text, context="document paragraphs")
        
        for segment in chunk:
            seg_idx = segment['seg_idx']
            seg_pattern = f"<SEG{seg_idx}>(.*?)</SEG{seg_idx}>"
            seg_match = re.search(seg_pattern, translated_combined, re.DOTALL)
            if seg_match:
                segment_translated = seg_match.group(1).strip()
                translatable_indices = segment_translatable_map[seg_idx]
                self._extract_translated_runs(segment_translated, segment['runs_list'], translatable_indices, 'seg', seg_idx)
                segment['full_text'] = "".join(run.get('translated_text', run['text']) for run in segment['runs_list'])
            else:
                for run in segment['runs_list']:
                    run['translated_text'] = run['text']
        
        if progress_callback: progress_callback()
        return chunk
    
    async def _translate_text_segments(self, text_segments: list[TextSegment], progress_callback=None):
        chunks = self._chunk_text_segments(text_segments)
        self.logger.info(f"📦 Split {len(text_segments)} text segments into {len(chunks)} chunks")
        tasks = [self._translate_text_chunk(chunk, progress_callback) for chunk in chunks]
        await asyncio.gather(*tasks)

    # --- Table Translation ---
    def _group_table_cells_by_table(self, table_cell_segments: list[TableCellSegment]) -> dict[int, list[TableCellSegment]]:
        grouped = defaultdict(list)
        for segment in table_cell_segments:
            grouped[segment['table_idx']].append(segment)
        return grouped
    
    async def _translate_table(self, table_idx: int, cells: list[TableCellSegment], progress_callback=None):
        if self.engine == "marian":
            await self._marian_translate_segment_runs(cells)
            if progress_callback: progress_callback()
            return

        marked_cells = []
        cell_translatable_map = {}
        for cell in cells:
            cell_id = f"{cell['table_idx']}-{cell['row_idx']}-{cell['cell_idx']}-{cell['para_idx']}"
            marked_text, translatable_indices = self._create_marked_text_from_runs(cell['runs_list'], 'cell', cell_id)
            cell_translatable_map[cell_id] = translatable_indices
            marked_cells.append(f"<CELL{cell_id}>\n{marked_text}\n</CELL{cell_id}>")
        
        combined_text = "\n\n".join(marked_cells)
        if combined_text.strip():
            translated_combined = await self._translate_text(combined_text, context=f"table {table_idx}")
            for cell in cells:
                cell_id = f"{cell['table_idx']}-{cell['row_idx']}-{cell['cell_idx']}-{cell['para_idx']}"
                cell_pattern = f"<CELL{cell_id}>(.*?)</CELL{cell_id}>"
                cell_match = re.search(cell_pattern, translated_combined, re.DOTALL)
                if cell_match:
                    cell_translated = cell_match.group(1).strip()
                    translatable_indices = cell_translatable_map[cell_id]
                    self._extract_translated_runs(cell_translated, cell['runs_list'], translatable_indices, 'cell', cell_id)
                else:
                    for run in cell['runs_list']:
                        run['translated_text'] = run['text']
        if progress_callback: progress_callback()

    async def _translate_table_cell_segments(self, table_cell_segments: list[TableCellSegment], progress_callback=None):
        grouped_tables = self._group_table_cells_by_table(table_cell_segments)
        tasks = [self._translate_table(table_idx, cells, progress_callback) for table_idx, cells in grouped_tables.items()]
        await asyncio.gather(*tasks)

    # --- Chart Translation ---
    def _group_charts_by_idx(self, chart_segments: list[ChartSegment]) -> dict[int, list[ChartSegment]]:
        grouped = defaultdict(list)
        for segment in chart_segments:
            grouped[segment['chart_idx']].append(segment)
        return grouped
    
    async def _translate_chart(self, chart_idx: int, elements: list[ChartSegment], progress_callback=None):
        if self.engine == "marian":
            await self._marian_process_texts(elements)
            if progress_callback: progress_callback()
            return

        marked_elements = []
        for elem in elements:
            elem_id = f"{chart_idx}-{elem['element_type']}-{elem['element_idx']}"
            if elem['text'].strip():
                marked_elements.append(f"<CHART{elem_id}>{elem['text']}</CHART{elem_id}>")
        
        combined_text = "\n\n".join(marked_elements)
        if combined_text.strip():
            translated_combined = await self._translate_text(combined_text, context=f"chart {chart_idx}")
            for elem in elements:
                elem_id = f"{chart_idx}-{elem['element_type']}-{elem['element_idx']}"
                pattern = f"<CHART{elem_id}>(.*?)</CHART{elem_id}>"
                match = re.search(pattern, translated_combined, re.DOTALL)
                if match:
                    elem['translated_text'] = match.group(1)
                else:
                    elem['translated_text'] = elem['text']
        if progress_callback: progress_callback()

    async def _translate_chart_segments(self, chart_segments: list[ChartSegment], progress_callback=None):
        grouped_charts = self._group_charts_by_idx(chart_segments)
        tasks = [self._translate_chart(chart_idx, elements, progress_callback) for chart_idx, elements in grouped_charts.items()]
        await asyncio.gather(*tasks)

    # --- SmartArt Translation ---
    def _group_smartarts_by_idx(self, smartart_segments: list[SmartArtSegment]) -> dict[int, list[SmartArtSegment]]:
        grouped = defaultdict(list)
        for segment in smartart_segments:
            grouped[segment['smartart_idx']].append(segment)
        return grouped
    
    async def _translate_smartart(self, smartart_idx: int, elements: list[SmartArtSegment], progress_callback=None):
        if self.engine == "marian":
            await self._marian_process_texts(elements)
            if progress_callback: progress_callback()
            return

        marked_elements = []
        for elem in elements:
            elem_id = f"{smartart_idx}-{elem['element_idx']}"
            if elem['text'].strip():
                marked_elements.append(f"<SMART{elem_id}>{elem['text']}</SMART{elem_id}>")
        
        combined_text = "\n\n".join(marked_elements)
        if combined_text.strip():
            translated_combined = await self._translate_text(combined_text, context=f"SmartArt {smartart_idx}")
            for elem in elements:
                elem_id = f"{smartart_idx}-{elem['element_idx']}"
                pattern = f"<SMART{elem_id}>(.*?)</SMART{elem_id}>"
                match = re.search(pattern, translated_combined, re.DOTALL)
                if match:
                    elem['translated_text'] = match.group(1)
                else:
                    elem['translated_text'] = elem['text']
        if progress_callback: progress_callback()

    async def _translate_smartart_segments(self, smartart_segments: list[SmartArtSegment], progress_callback=None):
        grouped_smartarts = self._group_smartarts_by_idx(smartart_segments)
        tasks = [self._translate_smartart(smartart_idx, elements, progress_callback) for smartart_idx, elements in grouped_smartarts.items()]
        await asyncio.gather(*tasks)

    # =========================================================================
    # HÀM ĐIỀU PHỐI CHÍNH
    # =========================================================================
    async def _translate_all(self):
        with open(self.checkpoint_file, "r", encoding="utf-8") as f:
            checkpoint_data = json.load(f)
        
        total_tasks = 0
        text_segments = checkpoint_data.get("text_segments", [])
        table_cell_segments = checkpoint_data.get("table_cell_segments", [])
        chart_segments = checkpoint_data.get("chart_segments", [])
        smartart_segments = checkpoint_data.get("smartart_segments", [])

        if text_segments: total_tasks += len(self._chunk_text_segments(text_segments))
        if table_cell_segments: total_tasks += len(self._group_table_cells_by_table(table_cell_segments))
        if chart_segments: total_tasks += len(self._group_charts_by_idx(chart_segments))
        if smartart_segments: total_tasks += len(self._group_smartarts_by_idx(smartart_segments))

        if total_tasks == 0:
            self.logger.info("No content to translate.")
            return
        
        with tqdm(total=total_tasks, desc="Translating content", unit="task") as pbar:
            progress_callback = pbar.update
            all_tasks = []
            if text_segments: all_tasks.append(self._translate_text_segments(text_segments, progress_callback))
            if table_cell_segments: all_tasks.append(self._translate_table_cell_segments(table_cell_segments, progress_callback))
            if chart_segments: all_tasks.append(self._translate_chart_segments(chart_segments, progress_callback))
            if smartart_segments: all_tasks.append(self._translate_smartart_segments(smartart_segments, progress_callback))
            
            if all_tasks:
                await asyncio.gather(*all_tasks)

        with open(self.checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
    
    @timer
    @log_errors
    def translate(self, progress_callback=None):
        asyncio.run(self._translate_all())