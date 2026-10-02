import os
import json
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from groq import Groq

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = "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"
client = Groq(api_key=GROQ_API_KEY)

class CourseData(BaseModel):
    program_name: str
    course_name: str
    course_type: str
    academic_year: int
    total_years: int
    num_plos: int
    program_outcomes: str
    course_description: str

# هذا السطر يجعل بايثون يفتح صفحة index.html فوراً عند زيارة الرابط
@app.get("/")
async def read_index():
    return FileResponse("index.html")

@app.post("/api/generate-matrix")
async def generate_matrix(data: CourseData):
    if data.course_type == "supportive":
        target_clos = 3
        clo_rule = "يحدد بـ 3 مخرجات تعلم (CLOs) كحد أقصى"
    else:
        progress_ratio = (data.academic_year - 1) / max(1, (data.total_years - 1))
        calculated_clos = int(4 + round(4 * progress_ratio))
        target_clos = max(4, min(8, calculated_clos))
        clo_rule = f"يستوجب صياغة ({target_clos}) مخرجات تعلم (CLOs) حصراً، ليتناسب مع المرحلة الدراسية"

    prompt = f"""
يُطلب إجراء تحليل أكاديمي لبيانات مقرر ضمن برنامج {data.program_name}.
طبيعة المقرر ({data.course_name}): {"مقرر أساسي" if data.course_type == "basic" else "مقرر ساند"}
المرحلة الدراسية: {data.academic_year} من إجمالي {data.total_years}.
الشرط الكمي: {clo_rule}.
إجمالي مخرجات البرنامج: {data.num_plos}.

مخرجات البرنامج (PLOs):
{data.program_outcomes}

المفردات والمحتوى العلمي:
{data.course_description}

المحددات الأكاديمية الصارمة:
1. تُصاغ مخرجات التعلم (CLOs) بصورة شمولية وقابلة للقياس، بحيث تعكس المحصلة المعرفية والمهارية للمقرر ككل.
2. يُمنع منعاً باتاً الإشارة المباشرة إلى أرقام المحاضرات (مثل: المحاضرة الأولى) أو عناوينها المستقلة داخل نص المخرج.
3. يُربط كل مخرج مقرر برقم مخرج البرنامج الأقرب له (من 1 إلى {data.num_plos}).
4. يُحدد مستوى التطبيق: I، R، أو M.
5. تُحدد طريقة التدريس (محاضرة / عملي / ورشة).
6. تُحدد أداة التقييم (اختبار / تقرير / مشروع).

يتم إخراج النتيجة بصيغة JSON حصراً بالشكل الآتي:
{{
  "mapping": [
    {{
      "clo": "نص مخرج تعلم المقرر",
      "plo_number": 1, 
      "level": "I",
      "teaching_method": "محاضرة",
      "assessment_tool": "اختبار"
    }}
  ]
}}
"""
    try:
        models_list = client.models.list()
        text_models = [m.id for m in models_list.data if not any(x in m.id.lower() for x in ["whisper", "guard", "vision", "orpheus"])]
        active_model = text_models[0] if text_models else models_list.data[0].id

        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You output only valid JSON in Arabic."},
                {"role": "user", "content": prompt}
            ],
            model=active_model,
            response_format={"type": "json_object"},
            temperature=0.2
        )

        content = chat_completion.choices[0].message.content.strip()
        cleaned_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.MULTILINE).strip()
        return json.loads(cleaned_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
