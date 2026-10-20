<template>
  <section class="patient-archive">
    <header class="archive-header">
      <div>
        <p class="eyebrow">PATIENT ARCHIVE</p>
        <h2>患者档案</h2>
        <p class="archive-subtitle">基本资料、量表结果、历史记录与报告统一管理。</p>
      </div>
      <div class="archive-actions">
        <el-button v-if="view === 'detail'" @click="backToList">返回患者列表</el-button>
        <el-button v-else type="primary" @click="openCreateDialog">新建患者</el-button>
      </div>
    </header>

    <div v-if="errorMessage" class="archive-error" role="alert">{{ errorMessage }}</div>

    <template v-if="view === 'list'">
      <div class="search-toolbar">
        <el-input
          v-model="search"
          clearable
          placeholder="按患者编号或姓名 / 化名搜索"
          @keyup.enter="loadPatients(true)"
          @clear="loadPatients(true)"
        />
        <el-button :loading="loadingPatients" @click="loadPatients(true)">搜索</el-button>
      </div>

      <el-table
        v-loading="loadingPatients"
        :data="patients"
        row-key="id"
        empty-text="暂无患者档案，点击“新建患者”添加虚拟患者"
        @row-click="openPatient"
      >
        <el-table-column prop="patient_code" label="患者编号" min-width="130" />
        <el-table-column prop="display_name" label="姓名 / 化名" min-width="140" />
        <el-table-column label="性别" width="100">
          <template #default="{ row }">{{ sexLabel(row.sex) }}</template>
        </el-table-column>
        <el-table-column prop="birth_date" label="出生日期" min-width="130">
          <template #default="{ row }">{{ row.birth_date || '未填写' }}</template>
        </el-table-column>
        <el-table-column prop="updated_at" label="最近更新" min-width="190">
          <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="openPatient(row)">查看档案</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-row">
        <span>共 {{ totalPatients }} 位患者</span>
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="totalPatients"
          layout="prev, pager, next"
          @current-change="loadPatients()"
        />
      </div>
    </template>

    <template v-else-if="selectedPatient">
      <section class="patient-summary">
        <div class="patient-avatar">{{ selectedPatient.display_name.slice(0, 1) }}</div>
        <div class="patient-summary-copy">
          <h3>{{ selectedPatient.display_name }}</h3>
          <p>患者编号：{{ selectedPatient.patient_code }}</p>
          <p v-if="currentPatientId === selectedPatient.id" class="current-patient-label">已关联到当前工作台</p>
        </div>
        <div class="patient-summary-actions">
          <el-button
            :type="currentPatientId === selectedPatient.id ? 'success' : 'primary'"
            @click="setAsCurrentPatient"
          >
            {{ currentPatientId === selectedPatient.id ? '当前患者' : '关联到工作台' }}
          </el-button>
          <el-button @click="openEditDialog">编辑资料</el-button>
          <el-button type="danger" plain @click="archiveCurrentPatient">归档患者</el-button>
        </div>
      </section>

      <el-tabs v-model="activeTab" class="patient-tabs" @tab-change="onTabChange">
        <el-tab-pane label="基本资料" name="overview">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="患者编号">{{ selectedPatient.patient_code }}</el-descriptions-item>
            <el-descriptions-item label="姓名 / 化名">{{ selectedPatient.display_name }}</el-descriptions-item>
            <el-descriptions-item label="性别">{{ sexLabel(selectedPatient.sex) }}</el-descriptions-item>
            <el-descriptions-item label="出生日期">{{ selectedPatient.birth_date || '未填写' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatDate(selectedPatient.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ formatDate(selectedPatient.updated_at) }}</el-descriptions-item>
            <el-descriptions-item label="备注" :span="2">
              <span class="notes-text">{{ selectedPatient.notes || '暂无备注' }}</span>
            </el-descriptions-item>
          </el-descriptions>
          <p class="privacy-hint">建议使用患者编号和化名。第一版请勿录入身份证号、住址等不必要的敏感信息。</p>
        </el-tab-pane>

        <el-tab-pane label="历史记录" name="history">
          <div class="tab-toolbar">
            <div>
              <h3>历史会话</h3>
              <p>仅显示明确选择“保存到患者历史”的会话。</p>
            </div>
            <el-button :loading="loadingDetails" @click="loadHistory">刷新</el-button>
          </div>
          <el-table :data="historyItems" v-loading="loadingDetails" empty-text="暂无已保存的会话">
            <el-table-column prop="title" label="会话标题" min-width="160" />
            <el-table-column label="消息数" width="90">
              <template #default="{ row }">{{ row.message_count }}</template>
            </el-table-column>
            <el-table-column label="最近内容" min-width="240">
              <template #default="{ row }">
                <span class="last-message">{{ row.last_message || '暂无消息' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="updated_at" label="更新时间" min-width="185">
              <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button link type="primary" @click="openHistory(row)">查看详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="量表结果" name="assessments">
          <div class="tab-toolbar">
            <div>
              <h3>量表结果</h3>
              <p>量表仅用于筛查，不能单独用于诊断。</p>
            </div>
            <el-button :loading="loadingDetails" @click="loadAssessments">刷新</el-button>
          </div>
          <el-table :data="assessmentItems" v-loading="loadingDetails" empty-text="暂无保存的量表结果">
            <el-table-column prop="scale_type" label="量表" width="110" />
            <el-table-column label="总分" width="100">
              <template #default="{ row }">{{ row.total }} / {{ row.scale_type === 'PHQ-9' ? 27 : 21 }}</template>
            </el-table-column>
            <el-table-column prop="severity_band" label="分数分层" min-width="190" />
            <el-table-column prop="created_at" label="测评时间" min-width="190">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="安全提示" min-width="110">
              <template #default="{ row }">
                <el-tag v-if="row.safety_alert" type="warning">需要关注</el-tag>
                <span v-else>—</span>
              </template>
            </el-table-column>
            <el-table-column label="详情" width="90">
              <template #default="{ row }">
                <el-button link type="primary" @click="openAssessment(row)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="报告管理" name="reports">
          <div class="tab-toolbar">
            <div>
              <h3>报告管理</h3>
              <p>支持 PDF、DOCX、PNG、JPG；单个文件最大 20 MB。分析结果仅供辅助阅读，请人工核对。</p>
            </div>
            <div class="report-actions">
              <input
                ref="reportInput"
                class="visually-hidden"
                type="file"
                accept=".pdf,.docx,.png,.jpg,.jpeg,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/png,image/jpeg"
                @change="uploadReport"
              />
              <el-button :loading="uploadingReport" type="primary" @click="chooseReport">
                上传报告
              </el-button>
              <el-button :loading="loadingDetails" @click="loadReports">刷新</el-button>
            </div>
          </div>
          <el-table :data="reportItems" v-loading="loadingDetails" empty-text="暂无报告">
            <el-table-column prop="original_filename" label="文件名" min-width="240" />
            <el-table-column label="大小" width="110">
              <template #default="{ row }">{{ formatBytes(row.size_bytes) }}</template>
            </el-table-column>
            <el-table-column prop="created_at" label="上传时间" min-width="190">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="300" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" :loading="analyzingReport && analyzingReportId === row.id" @click="analyzeReport(row)">分析</el-button>
                <el-button link type="primary" @click="viewAnalysisHistory(row)">历史</el-button>
                <el-button link type="primary" @click="downloadReport(row)">下载</el-button>
                <el-button link type="danger" @click="archiveReport(row)">归档</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </template>

    <el-dialog v-model="formVisible" :title="editingPatientId ? '编辑患者资料' : '新建患者档案'" width="560px">
      <el-form :model="form" label-width="110px" @submit.prevent>
        <el-form-item label="患者编号" required>
          <el-input v-model="form.patient_code" maxlength="64" placeholder="例如 DEMO-001" />
        </el-form-item>
        <el-form-item label="姓名 / 化名" required>
          <el-input v-model="form.display_name" maxlength="80" placeholder="建议使用化名" />
        </el-form-item>
        <el-form-item label="性别">
          <el-select v-model="form.sex" clearable placeholder="请选择" style="width: 100%">
            <el-option label="女" value="female" />
            <el-option label="男" value="male" />
            <el-option label="其他" value="other" />
            <el-option label="未说明" value="unknown" />
          </el-select>
        </el-form-item>
        <el-form-item label="出生日期">
          <el-date-picker
            v-model="form.birth_date"
            type="date"
            value-format="YYYY-MM-DD"
            format="YYYY-MM-DD"
            clearable
            placeholder="选择日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="3" maxlength="2000" show-word-limit placeholder="仅填写开展服务所必需的信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingPatient" @click="savePatient">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="historyDialogVisible" :title="historyDetail?.title || '历史会话'" width="760px">
      <div v-if="historyDetail" class="history-messages">
        <article
          v-for="(message, index) in historyDetail.messages"
          :key="`${message.created_at}-${index}`"
          class="history-message"
          :class="message.role === 'user' ? 'history-user' : 'history-assistant'"
        >
          <div class="history-message-meta">
            {{ message.role === 'user' ? '用户' : '心晴社区' }} · {{ formatDate(message.created_at) }}
          </div>
          <div class="history-message-content">{{ message.content }}</div>
        </article>
      </div>
      <el-empty v-else description="没有可显示的历史记录" />
    </el-dialog>

    <el-dialog v-model="assessmentDialogVisible" title="量表结果详情" width="520px">
      <template v-if="activeAssessment">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="量表">{{ activeAssessment.scale_type }}</el-descriptions-item>
          <el-descriptions-item label="总分">{{ activeAssessment.total }}</el-descriptions-item>
          <el-descriptions-item label="分数分层">{{ activeAssessment.severity_band }}</el-descriptions-item>
          <el-descriptions-item label="作答答案">{{ activeAssessment.answers.join(', ') }}</el-descriptions-item>
          <el-descriptions-item label="测评时间">{{ formatDate(activeAssessment.created_at) }}</el-descriptions-item>
        </el-descriptions>
        <div v-if="activeAssessment.safety_alert" class="assessment-safety-alert">
          <strong>安全提示</strong>
          <p>{{ activeAssessment.safety_alert }}</p>
        </div>
        <p class="privacy-hint">结果仅用于筛查，不构成诊断；如存在迫切危险，应立即联系当地急救服务或前往急诊。</p>
      </template>
    </el-dialog>
  </section>
    <!-- PSYCONSULT_REPORT_ANALYSIS_V1 -->
    <el-dialog v-model="analysisDialogVisible" title="心理测评报告分析" width="min(860px, 92vw)" destroy-on-close>
      <div v-loading="analyzingReport" class="report-analysis-dialog">
        <template v-if="analysisResult">
          <div class="analysis-meta">
            <p><strong>文件：</strong>{{ analysisHistoryReport?.original_filename || reportItems.find(item => item.id === analysisResult?.report_id)?.original_filename || '心理测评报告' }}</p>
            <p><strong>提取方式：</strong>{{ analysisResult.extraction_method }}　<strong>模型：</strong>{{ analysisResult.model_name }}</p>
            <p><strong>分析时间：</strong>{{ formatDate(analysisResult.created_at) }}</p>
          </div>
          <pre class="analysis-markdown">{{ analysisResult.analysis_markdown }}</pre>
          <el-collapse>
            <el-collapse-item title="查看提取的原始文本（请人工核对 OCR）" name="raw-text">
              <pre class="analysis-raw-text">{{ analysisResult.extracted_text }}</pre>
            </el-collapse-item>
          </el-collapse>
        </template>
        <el-empty v-else-if="analyzingReport" description="正在提取文本并分析，请稍候" />
      </div>
      <template #footer>
        <el-button @click="analysisDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="analysisHistoryDialogVisible" title="报告分析历史" width="760px">
      <el-table :data="analysisHistory" v-loading="analysisHistoryLoading" empty-text="暂无分析记录">
        <el-table-column prop="created_at" label="分析时间" min-width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="extraction_method" label="文本提取方式" min-width="130" />
        <el-table-column prop="model_name" label="模型" min-width="130" />
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openAnalysisDetail(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="analysisHistoryDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

interface Patient {
  id: string
  patient_code: string
  display_name: string
  sex: 'female' | 'male' | 'other' | 'unknown' | null
  birth_date: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

interface HistoryItem {
  session_id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
  last_message: string | null
}

interface HistoryMessage {
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

interface HistoryDetail {
  session_id: string
  title: string
  created_at: string
  updated_at: string
  messages: HistoryMessage[]
}

interface AssessmentItem {
  id: string
  patient_id: string
  scale_type: 'PHQ-9' | 'GAD-7'
  answers: number[]
  total: number
  severity_band: string
  safety_alert: string | null
  created_at: string
}

interface ReportItem {
  id: string
  patient_id: string
  original_filename: string
  content_type: string
  size_bytes: number
  sha256: string
  created_at: string
}

interface ReportAnalysisSummary {
  id: string
  patient_id: string
  report_id: string
  extraction_method: string
  model_name: string
  created_at: string
  preview?: string
}

interface ReportAnalysisDetail extends ReportAnalysisSummary {
  user_id: string
  extracted_text: string
  analysis_markdown: string
}

interface PatientForm {
  patient_code: string
  display_name: string
  sex: Patient['sex']
  birth_date: string | null
  notes: string
}

const props = defineProps<{
  apiBaseUrl: string
  apiAuthToken: string
  userId: string
  currentPatientId: string | null
}>()

const emit = defineEmits<{
  (event: 'patient-selected', patient: Patient | null): void
}>()

const view = ref<'list' | 'detail'>('list')
const activeTab = ref('overview')
const patients = ref<Patient[]>([])
const selectedPatient = ref<Patient | null>(null)
const search = ref('')
const page = ref(1)
const pageSize = 20
const totalPatients = ref(0)
const loadingPatients = ref(false)
const loadingDetails = ref(false)
const savingPatient = ref(false)
const uploadingReport = ref(false)
const errorMessage = ref('')
const formVisible = ref(false)
const editingPatientId = ref<string | null>(null)
const reportInput = ref<HTMLInputElement | null>(null)
const historyItems = ref<HistoryItem[]>([])
const assessmentItems = ref<AssessmentItem[]>([])
const reportItems = ref<ReportItem[]>([])
const analysisDialogVisible = ref(false)
const analysisHistoryDialogVisible = ref(false)
const analyzingReport = ref(false)
const analyzingReportId = ref<string | null>(null)
const analysisHistoryLoading = ref(false)
const analysisHistory = ref<ReportAnalysisSummary[]>([])
const analysisHistoryReport = ref<ReportItem | null>(null)
const analysisResult = ref<ReportAnalysisDetail | null>(null)
const historyDialogVisible = ref(false)
const historyDetail = ref<HistoryDetail | null>(null)
const assessmentDialogVisible = ref(false)
const activeAssessment = ref<AssessmentItem | null>(null)

const emptyForm = (): PatientForm => ({
  patient_code: '',
  display_name: '',
  sex: null,
  birth_date: null,
  notes: '',
})
const form = reactive<PatientForm>(emptyForm())

const apiRoot = () => props.apiBaseUrl.replace(/\/+$/, '')

function requestHeaders(jsonBody = false): Headers {
  const headers = new Headers()
  headers.set('X-User-Id', props.userId)
  if (props.apiAuthToken) headers.set('Authorization', `Bearer ${props.apiAuthToken}`)
  if (jsonBody) headers.set('Content-Type', 'application/json')
  return headers
}

async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const bodyIsFormData =
    typeof FormData !== 'undefined' &&
    typeof init.body === 'object' &&
    init.body !== null &&
    init.body instanceof FormData
  const headers = requestHeaders(Boolean(init.body) && !bodyIsFormData)
  new Headers(init.headers).forEach((value, key) => headers.set(key, value))
  const response = await fetch(`${apiRoot()}${path}`, { ...init, headers })
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof body?.detail === 'string' ? body.detail : `请求失败（HTTP ${response.status}）`
    throw new Error(detail)
  }
  return body as T
}

function showError(error: unknown) {
  errorMessage.value = error instanceof Error ? error.message : '请求失败，请稍后重试。'
}

async function loadPatients(resetPage = false) {
  if (resetPage) page.value = 1
  loadingPatients.value = true
  errorMessage.value = ''
  try {
    const query = new URLSearchParams({
      search: search.value.trim(),
      limit: String(pageSize),
      offset: String((page.value - 1) * pageSize),
    })
    const result = await apiRequest<{ items: Patient[]; total: number }>(`/api/patients?${query}`)
    patients.value = result.items
    totalPatients.value = result.total
  } catch (error) {
    showError(error)
  } finally {
    loadingPatients.value = false
  }
}

async function openPatient(patient: Patient) {
  selectedPatient.value = patient
  view.value = 'detail'
  activeTab.value = 'overview'
  await loadAllDetails()
}

function backToList() {
  view.value = 'list'
  selectedPatient.value = null
  errorMessage.value = ''
  void loadPatients()
}

async function loadAllDetails() {
  if (!selectedPatient.value) return
  loadingDetails.value = true
  errorMessage.value = ''
  const id = selectedPatient.value.id
  try {
    const [history, assessments, reports] = await Promise.all([
      apiRequest<{ items: HistoryItem[] }>(`/api/patients/${id}/history`),
      apiRequest<{ items: AssessmentItem[] }>(`/api/patients/${id}/assessments`),
      apiRequest<{ items: ReportItem[] }>(`/api/patients/${id}/reports`),
    ])
    historyItems.value = history.items
    assessmentItems.value = assessments.items
    reportItems.value = reports.items
  } catch (error) {
    showError(error)
  } finally {
    loadingDetails.value = false
  }
}

async function loadHistory() {
  if (!selectedPatient.value) return
  loadingDetails.value = true
  try {
    const result = await apiRequest<{ items: HistoryItem[] }>(
      `/api/patients/${selectedPatient.value.id}/history`,
    )
    historyItems.value = result.items
  } catch (error) {
    showError(error)
  } finally {
    loadingDetails.value = false
  }
}

async function loadAssessments() {
  if (!selectedPatient.value) return
  loadingDetails.value = true
  try {
    const result = await apiRequest<{ items: AssessmentItem[] }>(
      `/api/patients/${selectedPatient.value.id}/assessments`,
    )
    assessmentItems.value = result.items
  } catch (error) {
    showError(error)
  } finally {
    loadingDetails.value = false
  }
}

async function loadReports() {
  if (!selectedPatient.value) return
  loadingDetails.value = true
  try {
    const result = await apiRequest<{ items: ReportItem[] }>(
      `/api/patients/${selectedPatient.value.id}/reports`,
    )
    reportItems.value = result.items
  } catch (error) {
    showError(error)
  } finally {
    loadingDetails.value = false
  }
}

function onTabChange(name: string | number) {
  if (name === 'history') void loadHistory()
  if (name === 'assessments') void loadAssessments()
  if (name === 'reports') void loadReports()
}

function openCreateDialog() {
  editingPatientId.value = null
  Object.assign(form, emptyForm())
  formVisible.value = true
}

function openEditDialog() {
  if (!selectedPatient.value) return
  editingPatientId.value = selectedPatient.value.id
  Object.assign(form, {
    patient_code: selectedPatient.value.patient_code,
    display_name: selectedPatient.value.display_name,
    sex: selectedPatient.value.sex,
    birth_date: selectedPatient.value.birth_date,
    notes: selectedPatient.value.notes || '',
  })
  formVisible.value = true
}

async function savePatient() {
  if (!form.patient_code.trim() || !form.display_name.trim()) {
    ElMessage.warning('请填写患者编号和姓名 / 化名。')
    return
  }
  savingPatient.value = true
  errorMessage.value = ''
  try {
    const payload = {
      patient_code: form.patient_code.trim(),
      display_name: form.display_name.trim(),
      sex: form.sex || null,
      birth_date: form.birth_date || null,
      notes: form.notes.trim() || null,
    }
    const saved = await apiRequest<Patient>(
      editingPatientId.value ? `/api/patients/${editingPatientId.value}` : '/api/patients',
      {
        method: editingPatientId.value ? 'PATCH' : 'POST',
        body: JSON.stringify(payload),
      },
    )
    if (editingPatientId.value && selectedPatient.value?.id === saved.id) {
      selectedPatient.value = saved
    }
    if (props.currentPatientId === saved.id) {
      emit('patient-selected', saved)
    }
    formVisible.value = false
    ElMessage.success(editingPatientId.value ? '患者资料已更新' : '患者档案已创建')
    await loadPatients()
    if (!editingPatientId.value) {
      await openPatient(saved)
    }
  } catch (error) {
    showError(error)
    ElMessage.error(errorMessage.value)
  } finally {
    savingPatient.value = false
  }
}

function setAsCurrentPatient() {
  if (!selectedPatient.value) return
  emit('patient-selected', selectedPatient.value)
  ElMessage.success(`已关联患者：${selectedPatient.value.display_name}`)
}

async function archiveCurrentPatient() {
  if (!selectedPatient.value) return
  try {
    await ElMessageBox.confirm(
      '归档后该患者不会出现在默认列表中，但相关历史数据和报告文件不会自动物理删除。确定继续吗？',
      '归档患者',
      { type: 'warning', confirmButtonText: '确认归档', cancelButtonText: '取消' },
    )
    await apiRequest(`/api/patients/${selectedPatient.value.id}`, { method: 'DELETE' })
    if (props.currentPatientId === selectedPatient.value.id) emit('patient-selected', null)
    ElMessage.success('患者档案已归档')
    backToList()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      showError(error)
      ElMessage.error(errorMessage.value)
    }
  }
}

async function openHistory(item: HistoryItem) {
  if (!selectedPatient.value) return
  try {
    historyDetail.value = await apiRequest<HistoryDetail>(
      `/api/patients/${selectedPatient.value.id}/history/${encodeURIComponent(item.session_id)}`,
    )
    historyDialogVisible.value = true
  } catch (error) {
    showError(error)
  }
}

function openAssessment(item: AssessmentItem) {
  activeAssessment.value = item
  assessmentDialogVisible.value = true
}

function chooseReport() {
  reportInput.value?.click()
}

async function uploadReport(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !selectedPatient.value) return
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.warning('单个报告文件不能超过 20 MB。')
    return
  }
  if (!/\.(pdf|docx|png|jpe?g)$/i.test(file.name)) {
    ElMessage.warning('仅支持 PDF、DOCX、PNG 或 JPG 报告。')
    return
  }
  const body = new FormData()
  body.append('file', file)
  uploadingReport.value = true
  try {
    await apiRequest<ReportItem>(`/api/patients/${selectedPatient.value.id}/reports`, {
      method: 'POST',
      body,
    })
    ElMessage.success('报告上传成功')
    await loadReports()
  } catch (error) {
    showError(error)
    ElMessage.error(errorMessage.value)
  } finally {
    uploadingReport.value = false
  }
}

async function analyzeReport(report: ReportItem) {
  if (!selectedPatient.value) return
  analyzingReport.value = true
  analyzingReportId.value = report.id
  analysisResult.value = null
  analysisHistoryReport.value = report
  analysisDialogVisible.value = true
  try {
    const result = await apiRequest<ReportAnalysisDetail>(
      `/api/patients/${selectedPatient.value.id}/reports/${report.id}/analyze`,
      { method: 'POST' },
    )
    analysisResult.value = result
    ElMessage.success('报告分析完成，结果已保存到历史记录')
  } catch (error) {
    showError(error)
    ElMessage.error(errorMessage.value)
    analysisDialogVisible.value = false
  } finally {
    analyzingReport.value = false
    analyzingReportId.value = null
  }
}

async function viewAnalysisHistory(report: ReportItem) {
  if (!selectedPatient.value) return
  analysisHistoryReport.value = report
  analysisHistoryLoading.value = true
  try {
    const result = await apiRequest<{ items: ReportAnalysisSummary[] }>(
      `/api/patients/${selectedPatient.value.id}/reports/${report.id}/analyses`,
    )
    analysisHistory.value = result.items
    if (!result.items.length) {
      ElMessage.info('这份报告还没有分析记录，请先点击“分析”')
      return
    }
    analysisHistoryDialogVisible.value = true
  } catch (error) {
    showError(error)
    ElMessage.error(errorMessage.value)
  } finally {
    analysisHistoryLoading.value = false
  }
}

async function openAnalysisDetail(item: ReportAnalysisSummary) {
  if (!selectedPatient.value || !analysisHistoryReport.value) return
  try {
    const patientId = selectedPatient.value.id
    const reportId = analysisHistoryReport.value.id
    const detail = await apiRequest<ReportAnalysisDetail>(
      `/api/patients/${patientId}/reports/${reportId}/analyses/${item.id}`,
    )
    analysisResult.value = detail
    analysisHistoryDialogVisible.value = false
    analysisDialogVisible.value = true
  } catch (error) {
    showError(error)
    ElMessage.error(errorMessage.value)
  }
}

async function downloadReport(report: ReportItem) {
  if (!selectedPatient.value) return
  try {
    const headers = requestHeaders()
    const response = await fetch(
      `${apiRoot()}/api/patients/${selectedPatient.value.id}/reports/${report.id}/download`,
      { headers },
    )
    if (!response.ok) {
      const body = await response.json().catch(() => null)
      throw new Error(body?.detail || `下载失败（HTTP ${response.status}）`)
    }
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = report.original_filename
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  } catch (error) {
    showError(error)
    ElMessage.error(errorMessage.value)
  }
}

async function archiveReport(report: ReportItem) {
  if (!selectedPatient.value) return
  try {
    await ElMessageBox.confirm(
      `确定将报告“${report.original_filename}”归档吗？归档后不会出现在默认列表中。`,
      '归档报告',
      { type: 'warning', confirmButtonText: '确认归档', cancelButtonText: '取消' },
    )
    await apiRequest(
      `/api/patients/${selectedPatient.value.id}/reports/${report.id}`,
      { method: 'DELETE' },
    )
    ElMessage.success('报告已归档')
    await loadReports()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      showError(error)
      ElMessage.error(errorMessage.value)
    }
  }
}

function sexLabel(value: Patient['sex']) {
  const labels: Record<string, string> = {
    female: '女',
    male: '男',
    other: '其他',
    unknown: '未说明',
  }
  return value ? labels[value] || '未填写' : '未填写'
}

function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / (1024 * 1024)).toFixed(1)} MB`
}

watch(
  () => props.currentPatientId,
  async (id) => {
    if (!id || !patients.value.length) return
    const existing = patients.value.find((item) => item.id === id)
    if (existing) selectedPatient.value = existing
  },
)

onMounted(() => {
  void loadPatients()
})
</script>

<style scoped>
.patient-archive {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 22px;
  color: #243247;
}
.archive-header,
.search-toolbar,
.pagination-row,
.tab-toolbar,
.patient-summary,
.patient-summary-actions,
.report-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.archive-header h2 {
  margin: 0;
  font-size: 26px;
  color: #1f2e43;
}
.eyebrow {
  margin: 0 0 6px;
  color: #607287;
  font-size: 12px;
  font-weight: 700;
}
.archive-subtitle,
.tab-toolbar p {
  margin: 6px 0 0;
  color: #6a788b;
  font-size: 13px;
}
.archive-actions,
.report-actions {
  flex-shrink: 0;
}
.search-toolbar {
  justify-content: flex-start;
  max-width: 640px;
}
.search-toolbar .el-input {
  max-width: 460px;
}
.archive-error {
  padding: 10px 12px;
  border: 1px solid #f1c3c3;
  border-radius: 8px;
  background: #fff3f3;
  color: #a62e2e;
}
.pagination-row {
  justify-content: space-between;
  color: #6a788b;
  font-size: 13px;
}
.patient-summary {
  justify-content: flex-start;
  padding: 18px;
  border: 1px solid #dfe7ef;
  border-radius: 14px;
  background: #fff;
}
.patient-avatar {
  width: 48px;
  height: 48px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border-radius: 14px;
  background: #e6f3f5;
  color: #176e7c;
  font-size: 22px;
  font-weight: 700;
}
.patient-summary-copy {
  min-width: 0;
  flex: 1;
}
.patient-summary-copy h3 {
  margin: 0 0 6px;
  font-size: 20px;
}
.patient-summary-copy p {
  margin: 3px 0;
  color: #66758a;
  font-size: 13px;
}
.patient-summary-copy .current-patient-label {
  color: #13805d;
  font-weight: 600;
}
.patient-summary-actions {
  justify-content: flex-end;
  flex-wrap: wrap;
}
.patient-tabs {
  padding: 4px 16px 16px;
  border: 1px solid #dfe7ef;
  border-radius: 14px;
  background: #fff;
}
.patient-tabs :deep(.el-tabs__header) {
  margin-bottom: 18px;
}
.tab-toolbar {
  margin-bottom: 14px;
}
.tab-toolbar h3 {
  margin: 0;
  font-size: 16px;
}
.last-message {
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  white-space: normal;
  overflow-wrap: anywhere;
}
.notes-text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.privacy-hint {
  margin: 14px 0 0;
  color: #7a6a43;
  font-size: 12px;
  line-height: 1.6;
}
.history-messages {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-height: 60vh;
  overflow: auto;
}
.history-message {
  max-width: 92%;
  padding: 12px 14px;
  border: 1px solid #dfe7ef;
  border-radius: 12px;
}
.history-user {
  align-self: flex-end;
  background: #eaf3ff;
}
.history-assistant {
  align-self: flex-start;
  background: #f8fafc;
}
.history-message-meta {
  margin-bottom: 6px;
  color: #69788b;
  font-size: 12px;
}
.history-message-content {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  line-height: 1.6;
}
.assessment-safety-alert {
  margin-top: 14px;
  padding: 12px;
  border: 1px solid #edc58e;
  border-radius: 10px;
  background: #fff8e8;
  color: #744b14;
  line-height: 1.6;
}
.assessment-safety-alert p {
  margin: 6px 0 0;
}
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
@media (max-width: 850px) {
  .patient-archive {
    padding: 14px;
  }
  .archive-header,
  .patient-summary {
    align-items: flex-start;
    flex-wrap: wrap;
  }
  .patient-summary-actions {
    width: 100%;
  }
  .search-toolbar {
    max-width: none;
  }
  .tab-toolbar {
    align-items: flex-start;
    flex-wrap: wrap;
  }
}
.report-analysis-dialog {
  min-height: 120px;
  max-height: 68vh;
  overflow: auto;
}
.analysis-meta {
  margin-bottom: 14px;
  padding: 12px 14px;
  border-radius: 8px;
  background: var(--el-fill-color-light);
  overflow-wrap: anywhere;
}
.analysis-meta p { margin: 4px 0; }
.analysis-markdown,
.analysis-raw-text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
  font-family: inherit;
  line-height: 1.7;
  padding: 14px;
  border-radius: 8px;
  background: var(--el-bg-color-page);
}
.analysis-raw-text {
  max-height: 38vh;
  overflow: auto;
  font-size: 12px;
}

</style>
