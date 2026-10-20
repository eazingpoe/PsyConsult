<template>
  <div class="clinical-shell">
    <aside class="workspace-rail">
      <div class="brand-block">
        <div class="brand-mark">
          <el-icon><FirstAidKit /></el-icon>
        </div>
        <div>
          <p class="brand-kicker">COMMUNITY MENTAL HEALTH</p>
          <h1>心晴社区</h1>
        </div>
      </div>

      <el-button class="new-session-button" type="primary" :icon="CirclePlus" @click="createSession">
        新建对话
      </el-button>
      <el-button class="new-session-button" type="primary" @click="openAssessment">
        心理健康自评
      </el-button>
      <el-button class="new-session-button" type="primary" @click="openPatients">
        患者档案
      </el-button>
      <el-button v-if="activeView !== 'chat'" class="new-session-button secondary-nav-button" @click="openChat">
        聊天工作台
      </el-button>

      <nav class="session-list" aria-label="对话列表">
        <button
          v-for="s in sessions"
          :key="s.id"
          class="session-item"
          :class="{ active: s.id === currentSessionId }"
          type="button"
          @click="selectSession(s.id)"
        >
          <el-icon><ChatDotRound /></el-icon>
          <span>{{ s.name }}</span>
        </button>
      </nav>

      <div v-if="currentPatientId" class="active-patient-card">
        <div class="active-patient-avatar">{{ currentPatientName.slice(0, 1) || '患' }}</div>
        <div class="active-patient-copy">
          <span>当前关联患者</span>
          <strong>{{ currentPatientName }}</strong>
          <button type="button" @click="clearCurrentPatient">解除关联</button>
        </div>
      </div>

      <div class="doctor-card">
        <el-icon><UserFilled /></el-icon>
        <div>
          <span>当前用户</span>
          <strong>{{ userId }}</strong>
        </div>
      </div>
    </aside>

    <main v-if="activeView === 'chat'" class="case-workbench">
      <header class="case-header">
        <div>
          <p class="eyebrow">循证知识 · 心理自评 · 服务导航</p>
          <h2>心理健康服务工作台</h2>
        </div>
        <div v-if="currentPatientId" class="current-patient-banner">
          <el-icon><UserFilled /></el-icon>
          <span>当前患者：{{ currentPatientName }}</span>
        </div>
        <div class="service-pill" :class="{ active: isThinking }">
          <span class="status-dot"></span>
          {{ isThinking ? '推理中' : '待输入' }}
        </div>
      </header>

      <section class="notice-bar" aria-label="服务说明">
        <el-icon><WarningFilled /></el-icon>
        <span>本平台提供心理健康科普、自评信息与求助导航，不用于诊断或替代专业帮助。若你正面临紧急危险，请立即联系当地急救服务或前往最近急诊。</span>
      </section>

      <section ref="msgContainer" class="messages-panel" aria-live="polite">
        <div v-if="messages.length === 0" class="empty-state">
          <div class="empty-copy">
            <p class="eyebrow">快速开始</p>
            <h3>聊聊你正在经历的心理困扰，或提出心理健康问题。</h3>
            <p>你可以了解情绪与睡眠健康、查询心理健康知识、理解量表结果，或寻找合适的求助渠道。</p>
          </div>

          <div class="scenario-grid">
            <button
              v-for="scenario in scenarios"
              :key="scenario.title"
              class="scenario-card"
              type="button"
              @click="sendQuery(scenario.query)"
            >
              <span class="scenario-icon">
                <el-icon><component :is="scenario.icon" /></el-icon>
              </span>
              <span class="scenario-title">{{ scenario.title }}</span>
              <span class="scenario-text">{{ scenario.summary }}</span>
            </button>
          </div>
        </div>

        <article
          v-for="(msg, idx) in messages"
          :key="idx"
          class="message-row"
          :class="msg.role === 'user' ? 'user-row' : 'assistant-row'"
        >
          <div class="message-meta">
            <span>{{ msg.role === 'user' ? '你' : '心晴社区' }}</span>
          </div>
          <div class="message-bubble" :class="msg.role === 'user' ? 'user-bubble' : 'assistant-bubble'">
            <div v-if="msg.role === 'assistant' && msg.status" class="stage-status" aria-live="polite">
              <el-icon v-if="isThinking && idx === messages.length - 1" class="is-loading"><Loading /></el-icon>
              <span>阶段：{{ msg.status }}</span>
            </div>
            <div v-if="msg.content" class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
            <div
              v-if="msg.role === 'assistant' && msg.reportFile && msg.reportPatientId && !msg.reportArchived"
              class="report-message-actions"
            >
              <el-button
                size="small"
                :loading="Boolean(msg.reportArchiveBusy)"
                @click="archiveAnalyzedReport(msg)"
              >
                归档到 {{ msg.reportPatientName || '当前患者' }}
              </el-button>
              <span>保存原始报告，并在患者档案中保存分析记录。</span>
            </div>
            <div v-if="msg.reportArchived" class="report-archive-success">
              {{ msg.reportArchiveStatus === 'partial'
                ? '原始报告已归档，但分析记录保存失败'
                : msg.reportArchiveStatus === 'file_only'
                  ? '原始报告已保存，请在患者档案中检查'
                  : `已归档到 ${msg.reportPatientName || '患者档案'}` }}
            </div>
          </div>
        </article>

        <div v-if="isThinking" class="thinking-row">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>正在整理问题并检索相关知识</span>
        </div>
      </section>

      <footer class="composer">
        <div v-if="currentPatientId" class="save-history-toggle">
          <el-checkbox v-model="saveCurrentChat">
            将本次对话保存到 {{ currentPatientName }} 的历史记录
          </el-checkbox>
          <span>仅勾选后保存本次问答；未勾选时仍保留原有聊天与安全支持流程。</span>
        </div>
                <div class="voice-input-row">
          <button
            type="button"
            class="voice-record-button"
            :class="{ recording: isRecording }"
            :disabled="isThinking || isTranscribing"
            @click="toggleVoiceRecording"
          >
            <span class="voice-record-icon">{{ isRecording ? '■' : '🎙' }}</span>
            <span>{{ isRecording ? `停止录音 · ${formatVoiceDuration(recordingSeconds)}` : isTranscribing ? '正在转写…' : '录音转文字' }}</span>
          </button>
          <button
            type="button"
            class="report-upload-button"
            :disabled="isThinking || isTranscribing || isReportAnalyzing || isRecording"
            @click="triggerReportUpload"
          >
            <span aria-hidden="true">＋</span>
            <span>上传报告分析</span>
          </button>
          <input
            ref="reportFileInput"
            class="report-file-input"
            type="file"
            accept=".pdf,.docx,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            @change="handleReportFileChange"
          />
          <span v-if="isRecording" class="voice-status">正在录音，请自然讲话</span>
          <span v-else-if="isTranscribing" class="voice-status">正在识别语音，请稍候…</span>
          <span v-else class="voice-note">单次最长 4 分 50 秒。音频将发送到语音识别服务；请先征得录音者同意。</span>
          <span v-if="voiceError" class="voice-error">{{ voiceError }}</span>
          <span v-if="reportUploadError" class="voice-error">{{ reportUploadError }}</span>
        </div>
<el-input
          v-model="inputMessage"
          class="case-input"
          type="textarea"
          :autosize="{ minRows: 3, maxRows: 6 }"
          resize="none"
          placeholder="描述你遇到的心理困扰，或询问心理健康知识与求助资源"
          @keydown.enter.exact.prevent="sendQuery()"
        />
        <el-button
          class="send-button"
          type="primary"
          :icon="Promotion"
          :disabled="!inputMessage.trim() || isThinking || isReportAnalyzing"
          @click="sendQuery()"
        >
          发送
        </el-button>
      </footer>
    </main>

    <main v-else-if="activeView === 'assessment'" class="case-workbench" style="grid-column: 2 / -1; min-width: 0;">
      <header class="case-header">
        <div>
          <p class="eyebrow">COMMUNITY MENTAL HEALTH · SELF-ASSESSMENT</p>
          <h2>心理健康自评</h2>
        </div>
        <el-button @click="openChat">返回聊天工作台</el-button>
      </header>
      <AssessmentView
        :api-base-url="apiBaseUrl"
        :api-auth-token="apiAuthToken"
        :user-id="userId"
        :patient-id="currentPatientId"
      />
    </main>

    <main v-else class="case-workbench archive-workbench" style="grid-column: 2 / -1; min-width: 0;">
      <PatientArchiveView
        :api-base-url="apiBaseUrl"
        :api-auth-token="apiAuthToken"
        :user-id="userId"
        :current-patient-id="currentPatientId"
        @patient-selected="setCurrentPatient"
      />
    </main>

    <aside v-if="activeView === 'chat'" class="insight-panel">
      <section class="panel-section">
        <p class="section-label">服务流程</p>
        <ol class="pipeline-list">
          <li v-for="stage in pipelineStages" :key="stage.name">
            <span class="pipeline-index">{{ stage.index }}</span>
            <div>
              <strong>{{ stage.name }}</strong>
              <span>{{ stage.detail }}</span>
            </div>
          </li>
        </ol>
      </section>

      <section class="panel-section">
        <p class="section-label">知识源</p>
        <div class="source-list">
          <div v-for="source in knowledgeSources" :key="source.name" class="source-item">
            <el-icon><component :is="source.icon" /></el-icon>
            <div>
              <strong>{{ source.name }}</strong>
              <span>{{ source.detail }}</span>
            </div>
          </div>
        </div>
      </section>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'
import {
  ChatDotRound,
  CirclePlus,
  Connection,
  DataAnalysis,
  DocumentChecked,
  FirstAidKit,
  Loading,
  Promotion,
  UserFilled,
  WarningFilled,
} from '@element-plus/icons-vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import AssessmentView from './components/AssessmentView.vue'
import PatientArchiveView from './components/PatientArchiveView.vue'

interface PatientSelection {
  id: string
  display_name: string
}

interface SessionItem {
  id: string
  name: string
  patientId?: string | null
  patientName?: string
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  status?: string
  reportFile?: File
  reportPatientId?: string | null
  reportPatientName?: string
  reportArchived?: boolean
  reportArchiveBusy?: boolean
  reportArchiveStatus?: 'success' | 'partial' | 'file_only'
}

const activeView = ref<'chat' | 'assessment' | 'patients'>('chat')
const userId = ref(import.meta.env.VITE_API_USER_ID || 'doctor_001')
const currentPatientId = ref<string | null>(null)
const currentPatientName = ref('')
const saveCurrentChat = ref(false)
const currentSessionId = ref(`session_${Date.now()}`)
const sessions = ref<SessionItem[]>([{ id: currentSessionId.value, name: '新诊疗会话', patientId: null, patientName: '' }])
const messagesBySession = ref<Record<string, ChatMessage[]>>({
  [currentSessionId.value]: [],
})
const messages = ref<ChatMessage[]>([])
const inputMessage = ref('')
const isThinking = ref(false)
const msgContainer = ref<HTMLElement | null>(null)
const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '')
const apiAuthToken = import.meta.env.VITE_API_AUTH_TOKEN || ''

const scenarios = [
  {
    title: '情绪与睡眠',
    summary: '了解常见困扰与日常应对',
    icon: DataAnalysis,
    query: '最近我经常情绪低落、睡不好，可以从哪些方面了解和改善自己的心理状态？',
  },
  {
    title: '认识心理自评',
    summary: '了解 PHQ-9、GAD-7 的用途',
    icon: DocumentChecked,
    query: 'PHQ-9 和 GAD-7 是什么量表？它们的分数应该如何理解？',
  },
  {
    title: '心理健康知识',
    summary: '查找有来源支持的信息',
    icon: Connection,
    query: '请介绍如何识别可靠的心理健康信息，以及回答中的参考来源应该如何核实。',
  },
  {
    title: '寻找求助渠道',
    summary: '了解何时及如何寻求帮助',
    icon: FirstAidKit,
    query: '如果心理困扰持续影响睡眠和日常生活，可以考虑哪些求助渠道？',
  },
]

const pipelineStages = [
  { index: '01', name: '问题识别', detail: '识别心理健康问题与服务需求' },
  { index: '02', name: '循证检索', detail: '检索相关知识并保留来源信息' },
  { index: '03', name: '信息解释', detail: '区分检索证据与一般性说明' },
  { index: '04', name: '安全与求助', detail: '高风险表达优先进入安全支持流程' },
]

const knowledgeSources = [
  { name: 'Milvus 向量检索', detail: '心理健康知识资料与来源', icon: DataAnalysis },
  { name: 'Neo4j 知识图谱', detail: '相关概念与知识关系', icon: Connection },
  { name: 'Redis 会话上下文', detail: '辅助保持当前对话连续性', icon: ChatDotRound },
]

function renderMarkdown(text: string) {
  const html = marked.parse(text, { breaks: true, gfm: true }) as string
  return DOMPurify.sanitize(html)
}

function getSessionMessages(sessionId: string): ChatMessage[] {
  if (!messagesBySession.value[sessionId]) {
    messagesBySession.value[sessionId] = []
  }
  return messagesBySession.value[sessionId]
}

function setCurrentSessionMessages(sessionId: string) {
  messages.value = getSessionMessages(sessionId)
}

async function selectSession(sessionId: string) {
  const target = sessions.value.find((session) => session.id === sessionId)
  if (target) {
    currentPatientId.value = target.patientId || null
    currentPatientName.value = target.patientName || ''
  }
  saveCurrentChat.value = false
  activeView.value = 'chat'
  currentSessionId.value = sessionId
  setCurrentSessionMessages(sessionId)
  await scrollMessages()
}

function createSession() {
  activeView.value = 'chat'
  saveCurrentChat.value = false
  const id = `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  sessions.value.unshift({
    id,
    name: `对话 ${sessions.value.length + 1}`,
    patientId: currentPatientId.value,
    patientName: currentPatientName.value,
  })
  messagesBySession.value[id] = []
  currentSessionId.value = id
  setCurrentSessionMessages(id)
}

async function scrollMessages() {
  await nextTick()
  if (msgContainer.value) {
    msgContainer.value.scrollTop = msgContainer.value.scrollHeight
  }
}

function agentLabel(name: string): string {
  const labels: Record<string, string> = {
    orchestrator: '🧭 服务意图识别',
    differential_diagnosis: '🧠 心理健康信息整理',
    treatment_recommend: '📚 心理健康知识问答',
    drug_interaction: '📘 用药相关科普信息',
    safety_gate: '🛡️ 安全检查',
    safety_support: '🆘 安全支持',
    semantic_cache: '📚 缓存回答',
    input_validation: '📝 问题校验',
  }
  return labels[name] || name
}

function statusLabel(parsed: { status?: string; agent?: string; content?: string }): string {
  if (parsed.status === 'agent_node_start' && parsed.agent) {
    return `正在${agentLabel(parsed.agent)}...`
  }
  if (parsed.status === 'agent_tool_call') {
    return parsed.content || '正在查询知识库...'
  }
  if (parsed.status === 'agent_tool_done') {
    return parsed.content || '工具查询完成'
  }
  if (parsed.status === 'agent_node_complete' && parsed.agent) {
    return `${agentLabel(parsed.agent)} 已完成`
  }
  return parsed.content || ''
}

function appendAssistantMessage(sessionId: string, index: number, content: string) {
  const message = getSessionMessages(sessionId)[index]
  if (message && message.role === 'assistant') {
    message.content += content
  }
}

function replaceAssistantMessage(sessionId: string, index: number, content: string) {
  const message = getSessionMessages(sessionId)[index]
  if (message && message.role === 'assistant') {
    message.content = content
    message.status = undefined
  }
}

function updateAssistantStatus(sessionId: string, index: number, status: string) {
  const message = getSessionMessages(sessionId)[index]
  if (message && message.role === 'assistant') {
    message.status = status
  }
}

function openAssessment() {
  activeView.value = 'assessment'
}

function openPatients() {
  activeView.value = 'patients'
}

function openChat() {
  activeView.value = 'chat'
}

function setCurrentPatient(patient: PatientSelection | null) {
  const nextPatientId = patient?.id || null
  if (currentPatientId.value !== nextPatientId && messages.value.length > 0) {
    // Do not carry one patient's prior chat context into another patient's session.
    const id = `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
    sessions.value.unshift({
      id,
      name: '新患者会话',
      patientId: nextPatientId,
      patientName: patient?.display_name || '',
    })
    messagesBySession.value[id] = []
    currentSessionId.value = id
    setCurrentSessionMessages(id)
  }
  currentPatientId.value = nextPatientId
  currentPatientName.value = patient?.display_name || ''
  const activeSession = sessions.value.find((session) => session.id === currentSessionId.value)
  if (activeSession) {
    activeSession.patientId = nextPatientId
    activeSession.patientName = currentPatientName.value
  }
  if (nextPatientId) {
    sessions.value.forEach((session) => {
      if (session.patientId === nextPatientId) {
        session.patientName = currentPatientName.value
      }
    })
  }
  saveCurrentChat.value = false
}

function clearCurrentPatient() {
  setCurrentPatient(null)
}

// Voice input: record locally, transcribe on the backend, and let the user review before sending.
const isRecording = ref(false)
const isTranscribing = ref(false)
const voiceError = ref('')
const recordingSeconds = ref(0)
const MAX_RECORDING_SECONDS = 290
const MAX_AUDIO_BYTES = 7 * 1024 * 1024
const reportFileInput = ref<HTMLInputElement | null>(null)
const isReportAnalyzing = ref(false)
const reportUploadError = ref('')
let voiceRecorder: MediaRecorder | null = null
let voiceStream: MediaStream | null = null
let voiceChunks: BlobPart[] = []
let voiceTimer: number | null = null
let voiceRecordingStartedAt = 0

function formatVoiceDuration(totalSeconds: number): string {
  const safeSeconds = Math.max(0, totalSeconds)
  const minutes = Math.floor(safeSeconds / 60).toString().padStart(2, '0')
  const seconds = (safeSeconds % 60).toString().padStart(2, '0')
  return `${minutes}:${seconds}`
}

function clearVoiceTimer() {
  if (voiceTimer !== null) {
    window.clearInterval(voiceTimer)
    voiceTimer = null
  }
}

function stopVoiceRecording() {
  clearVoiceTimer()
  if (voiceRecorder && voiceRecorder.state !== 'inactive') {
    voiceRecorder.stop()
  } else {
    voiceStream?.getTracks().forEach((track) => track.stop())
    voiceStream = null
    isRecording.value = false
  }
}

async function startVoiceRecording() {
  voiceError.value = ''
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
    voiceError.value = '当前浏览器不支持录音，请使用最新版 Chrome/Edge，并通过 localhost 或 HTTPS 访问。'
    return
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    })
    voiceStream = stream
    const mimeCandidates = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/mp4',
    ]
    const preferredMime = mimeCandidates.find((mime) => MediaRecorder.isTypeSupported(mime))
    const recorder = preferredMime
      ? new MediaRecorder(stream, { mimeType: preferredMime })
      : new MediaRecorder(stream)
    voiceRecorder = recorder
    voiceChunks = []
    let recordingFailed = false

    recorder.ondataavailable = (event: BlobEvent) => {
      if (event.data && event.data.size > 0) voiceChunks.push(event.data)
    }
    recorder.onerror = () => {
      recordingFailed = true
      voiceError.value = '录音过程出现错误，请检查麦克风权限后重新录制。'
      clearVoiceTimer()
      isRecording.value = false
      voiceStream?.getTracks().forEach((track) => track.stop())
      voiceStream = null
    }
    recorder.onstop = () => {
      clearVoiceTimer()
      isRecording.value = false
      voiceStream?.getTracks().forEach((track) => track.stop())
      voiceStream = null
      voiceRecorder = null
      const blob = new Blob(voiceChunks, { type: recorder.mimeType || preferredMime || 'audio/webm' })
      voiceChunks = []
      if (recordingFailed) return
      if (!blob.size) {
        voiceError.value = '没有录到有效音频，请检查麦克风后重试。'
        return
      }
      void transcribeVoiceBlob(blob)
    }

    recorder.start(250)
    voiceRecordingStartedAt = Date.now()
    recordingSeconds.value = 0
    isRecording.value = true
    voiceTimer = window.setInterval(() => {
      recordingSeconds.value = Math.floor((Date.now() - voiceRecordingStartedAt) / 1000)
      if (recordingSeconds.value >= MAX_RECORDING_SECONDS) stopVoiceRecording()
    }, 500)
  } catch (error) {
    voiceStream?.getTracks().forEach((track) => track.stop())
    voiceStream = null
    isRecording.value = false
    voiceError.value = error instanceof Error && error.name === 'NotAllowedError'
      ? '麦克风权限被拒绝。请在浏览器地址栏允许麦克风访问后重试。'
      : '无法启动录音，请确认麦克风已连接且未被其他程序占用。'
  }
}

async function transcribeVoiceBlob(blob: Blob) {
  if (blob.size > MAX_AUDIO_BYTES) {
    voiceError.value = '录音文件超过大小限制，请缩短录音后重试。'
    return
  }

  isTranscribing.value = true
  voiceError.value = ''
  try {
    const mime = (blob.type || 'audio/webm').split(';', 1)[0]?.toLowerCase() || 'audio/webm'
    const extension = mime === 'audio/mp4' ? 'm4a'
      : mime === 'audio/ogg' ? 'ogg'
      : mime === 'audio/wav' ? 'wav'
      : mime === 'audio/mpeg' ? 'mp3'
      : 'webm'
    const formData = new FormData()
    formData.append('file', blob, `recording.${extension}`)

    const headers: Record<string, string> = { 'X-User-Id': userId.value }
    if (apiAuthToken) headers.Authorization = `Bearer ${apiAuthToken}`
    const response = await fetch(`${apiBaseUrl}/api/transcribe`, {
      method: 'POST',
      headers,
      body: formData,
    })
    let payload: { text?: string; detail?: string } = {}
    try {
      payload = await response.json()
    } catch {
      // Keep the generic error below if the server returned a non-JSON response.
    }
    if (!response.ok) {
      throw new Error(payload.detail || `语音识别请求失败（HTTP ${response.status}）。`)
    }
    const transcript = (payload.text || '').trim()
    if (!transcript) throw new Error('没有识别到文字，请重试。')

    const existing = inputMessage.value.trim()
    inputMessage.value = existing ? `${existing}\n${transcript}` : transcript
    voiceError.value = ''
  } catch (error) {
    voiceError.value = error instanceof Error
      ? error.message
      : '语音识别失败，请稍后重试。'
  } finally {
    isTranscribing.value = false
  }
}

function toggleVoiceRecording() {
  if (isRecording.value) {
    stopVoiceRecording()
  } else if (!isTranscribing.value && !isThinking.value) {
    void startVoiceRecording()
  }
}


function triggerReportUpload() {
  reportUploadError.value = ''
  reportFileInput.value?.click()
}

async function handleReportFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  target.value = ''
  reportUploadError.value = ''
  if (!file) return

  const extension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
  const allowedExtensions = ['.pdf', '.docx', '.png', '.jpg', '.jpeg']
  if (!allowedExtensions.includes(extension)) {
    reportUploadError.value = '文件格式不支持，请选择 PDF、DOCX、PNG 或 JPG/JPEG。'
    return
  }
  if (file.size <= 0) {
    reportUploadError.value = '所选文件为空，请重新选择。'
    return
  }
  if (file.size > 20 * 1024 * 1024) {
    reportUploadError.value = '报告文件不能超过 20 MB。'
    return
  }
  if (isThinking.value || isTranscribing.value || isReportAnalyzing.value) {
    reportUploadError.value = '当前有任务正在处理，请稍后再上传。'
    return
  }

  const sessionIdAtUpload = currentSessionId.value
  const patientIdAtUpload = currentPatientId.value
  const patientNameAtUpload = currentPatientName.value
  const targetMessages = getSessionMessages(sessionIdAtUpload)
  targetMessages.push({
    role: 'user',
    content: `上传心理测评报告：${file.name}`,
  })
  const assistantMessage: ChatMessage = {
    role: 'assistant',
    content: '正在提取报告文本并生成分析，请稍候……',
    status: '报告分析中',
  }
  targetMessages.push(assistantMessage)
  isReportAnalyzing.value = true
  await scrollMessages()

  try {
    const formData = new FormData()
    formData.append('file', file, file.name)
    const headers: Record<string, string> = { 'X-User-Id': userId.value }
    if (apiAuthToken) headers.Authorization = `Bearer ${apiAuthToken}`

    const response = await fetch(`${apiBaseUrl}/api/chat/report-analysis`, {
      method: 'POST',
      headers,
      body: formData,
    })

    let payload: Record<string, unknown> = {}
    try {
      const value: unknown = await response.json()
      if (value && typeof value === 'object') {
        payload = value as Record<string, unknown>
      }
    } catch {
      // Use the generic HTTP error if the server did not return JSON.
    }

    if (!response.ok) {
      const detail = typeof payload.detail === 'string' ? payload.detail : ''
      throw new Error(detail || `报告分析失败（HTTP ${response.status}）。`)
    }

    const analysis = typeof payload.analysis_markdown === 'string'
      ? payload.analysis_markdown.trim()
      : ''
    if (!analysis) {
      throw new Error('服务未返回有效的报告分析正文，请检查后端日志。')
    }

    assistantMessage.content = analysis
    assistantMessage.status = '回复完成'
    assistantMessage.reportFile = file
    assistantMessage.reportPatientId = patientIdAtUpload
    assistantMessage.reportPatientName = patientNameAtUpload
    assistantMessage.reportArchived = false

    if (!patientIdAtUpload) {
      assistantMessage.content +=
        '\n\n> 提示：本次分析未关联患者档案，报告文件仅用于本次分析，不会自动保存到服务器。若要归档，请先在左侧选择患者，再重新上传报告。'
    }
  } catch (error) {
    assistantMessage.status = '分析失败'
    assistantMessage.content = `报告分析失败：${error instanceof Error ? error.message : String(error)}`
  } finally {
    isReportAnalyzing.value = false
    if (currentSessionId.value === sessionIdAtUpload) {
      await scrollMessages()
    }
  }
}

async function archiveAnalyzedReport(message: ChatMessage) {
  const file = message.reportFile
  const patientId = message.reportPatientId
  if (!file || !patientId || message.reportArchived || message.reportArchiveBusy) return

  message.reportArchiveBusy = true
  let originalReportUploaded = false
  const headers: Record<string, string> = { 'X-User-Id': userId.value }
  if (apiAuthToken) headers.Authorization = `Bearer ${apiAuthToken}`

  const readPayload = async (response: Response): Promise<Record<string, unknown>> => {
    try {
      const value: unknown = await response.json()
      return value && typeof value === 'object'
        ? value as Record<string, unknown>
        : {}
    } catch {
      return {}
    }
  }
  const responseError = (payload: Record<string, unknown>, response: Response) => {
    return typeof payload.detail === 'string'
      ? payload.detail
      : `HTTP ${response.status}`
  }

  try {
    const formData = new FormData()
    formData.append('file', file, file.name)
    const uploadResponse = await fetch(
      `${apiBaseUrl}/api/patients/${encodeURIComponent(patientId)}/reports`,
      { method: 'POST', headers, body: formData },
    )
    const uploadPayload = await readPayload(uploadResponse)
    if (!uploadResponse.ok) {
      throw new Error(responseError(uploadPayload, uploadResponse))
    }
    originalReportUploaded = true

    const reportIdValue = uploadPayload.id ?? uploadPayload.report_id ?? uploadPayload.reportId
    const reportId = typeof reportIdValue === 'string' || typeof reportIdValue === 'number'
      ? String(reportIdValue)
      : ''
    if (!reportId) {
      message.reportArchived = true
      message.reportArchiveStatus = 'file_only'
      message.content +=
        '\n\n**归档状态：** 原始报告已上传，但接口未返回报告 ID，无法自动保存分析记录。请在患者档案中检查该报告。'
      return
    }

    const analysisResponse = await fetch(
      `${apiBaseUrl}/api/patients/${encodeURIComponent(patientId)}/reports/${encodeURIComponent(reportId)}/analyze`,
      { method: 'POST', headers },
    )
    const analysisPayload = await readPayload(analysisResponse)
    if (!analysisResponse.ok) {
      throw new Error(responseError(analysisPayload, analysisResponse))
    }

    message.reportArchived = true
    message.reportArchiveStatus = 'success'
    message.content +=
      `\n\n---\n**已归档：** 原始报告及分析记录已保存到患者档案「${message.reportPatientName || '当前患者'}」。`
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error)
    if (originalReportUploaded) {
      message.reportArchived = true
      message.reportArchiveStatus = 'partial'
      message.content +=
        `\n\n**部分完成：** 原始报告已归档，但分析记录保存失败（${detail}）。请在患者档案中重新分析该报告。`
    } else {
      message.content += `\n\n**归档失败：** ${detail}。你可以检查网络或后端日志后重试。`
    }
  } finally {
    message.reportArchiveBusy = false
  }
}

async function sendQuery(preset?: string) {
  const query = (preset || inputMessage.value).trim()
  if (!query || isThinking.value || isReportAnalyzing.value) return

  // 显式页面导航由前端处理，不调用聊天 API。
  const normalizedNavigationCommand = query
    .replace(/[“”‘’「」『』【】"'`]/g, '')
    .replace(/\s+/g, '')
  
  const requestsAssessmentNavigation =
    /(?:打开|进入|切换到|跳转到|前往|带我去|帮我打开)/.test(
      normalizedNavigationCommand
    ) &&
    /(?:心理健康自评|自评页面|自评功能|量表自评|PHQ-?9自评|GAD-?7自评)/i.test(
      normalizedNavigationCommand
    )
  
  if (requestsAssessmentNavigation) {
    inputMessage.value = ''
    openAssessment()
    return
  }

  const requestSessionId = currentSessionId.value
  const sessionMessages = getSessionMessages(requestSessionId)
  setCurrentSessionMessages(requestSessionId)

  sessionMessages.push({ role: 'user', content: query })
  inputMessage.value = ''
  isThinking.value = true

  const assistantIndex = sessionMessages.length
  sessionMessages.push({
    role: 'assistant',
    content: '',
    status: '正在连接服务...',
  })

  type ChatSseEvent = {
    status?: string
    agent?: string
    content?: string
    error?: string
    done?: boolean
  }

  let reader: ReadableStreamDefaultReader<Uint8Array> | null = null
  let buffer = ''
  let activeContentAgent = ''
  let receivedContent = false
  let streamFinished = false
  let streamFailed = false

  const processFrame = (frame: string) => {
    const payload = frame
      .split(/\r?\n/)
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).replace(/^ /, ''))
      .join('\n')

    if (!payload.trim()) return

    if (payload.trim() === '[DONE]') {
      streamFinished = true
      return
    }

    let event: ChatSseEvent

    try {
      event = JSON.parse(payload) as ChatSseEvent
    } catch (error) {
      console.warn('忽略无法解析的 SSE 事件', error)
      return
    }

    // 后端明确发送结束事件
    if (event.done === true) {
      streamFinished = true
      updateAssistantStatus(requestSessionId, assistantIndex, '回复完成')
      return
    }

    // 状态事件只更新阶段，不把进度文字混入回答正文
    if (event.status) {
      if (event.status === 'error' || event.status === 'failed') {
        const detail =
          event.content?.trim() ||
          event.error ||
          '后端处理失败，请稍后重试。'

        const current =
          getSessionMessages(requestSessionId)[assistantIndex]

        if (current?.content.trim()) {
          appendAssistantMessage(
            requestSessionId,
            assistantIndex,
            `\n\n> ⚠️ ${detail}`,
          )
        } else {
          replaceAssistantMessage(
            requestSessionId,
            assistantIndex,
            `请求失败：${detail}`,
          )
        }

        updateAssistantStatus(requestSessionId, assistantIndex, '请求失败')
        streamFailed = true
        return
      }

      const label = statusLabel(event)
      if (label) {
        updateAssistantStatus(requestSessionId, assistantIndex, label)
      }
      return
    }

    // 正文事件：例如 treatment_recommend、safety_support、
    // semantic_cache。相同 Agent 的多个事件必须按顺序拼接。
    if (typeof event.content !== 'string' || !event.content.length) return

    const incomingAgent = event.agent || 'assistant'

    if (!activeContentAgent) {
      activeContentAgent = incomingAgent
      replaceAssistantMessage(
        requestSessionId,
        assistantIndex,
        event.content,
      )
    } else if (incomingAgent === activeContentAgent) {
      appendAssistantMessage(
        requestSessionId,
        assistantIndex,
        event.content,
      )
    } else {
      // 不丢弃不同来源已经收到的正文，也不直接覆盖旧内容。
      activeContentAgent = incomingAgent
      appendAssistantMessage(
        requestSessionId,
        assistantIndex,
        `\n\n${event.content}`,
      )
    }

    receivedContent = true
    void scrollMessages()
  }

  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-User-Id': userId.value,
    }

    if (apiAuthToken) {
      headers.Authorization = `Bearer ${apiAuthToken}`
    }

    const response = await fetch(`${apiBaseUrl}/api/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        query,
        session_id: requestSessionId,
        patient_id: currentPatientId.value || undefined,
        save_to_history: Boolean(currentPatientId.value && saveCurrentChat.value),
      }),
    })

    if (!response.ok) {
      const detail = await response.text()
      throw new Error(
        `HTTP ${response.status}${detail ? `: ${detail.slice(0, 180)}` : ''}`,
      )
    }

    if (!response.body) {
      throw new Error('后端没有返回可读取的响应流。')
    }

    const contentType = response.headers.get('content-type') || ''

    if (!contentType.toLowerCase().includes('text/event-stream')) {
      const detail = await response.text()
      throw new Error(
        `后端未返回 SSE 流（${contentType || '未知响应类型'}）` +
        `${detail ? `：${detail.slice(0, 180)}` : ''}`,
      )
    }

    reader = response.body.getReader()
    const decoder = new TextDecoder()

    // 按 SSE 空行分隔事件，不假设一次网络读取就对应一个完整事件。
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      buffer = buffer.replace(/\r\n/g, '\n')

      let boundary = buffer.indexOf('\n\n')

      while (boundary !== -1) {
        const frame = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)

        processFrame(frame)
        boundary = buffer.indexOf('\n\n')
      }
    }

    // 刷出解码器内部缓存，并处理没有以空行结束的最后一个事件。
    buffer += decoder.decode()
    buffer = buffer.replace(/\r\n/g, '\n')

    let boundary = buffer.indexOf('\n\n')

    while (boundary !== -1) {
      processFrame(buffer.slice(0, boundary))
      buffer = buffer.slice(boundary + 2)
      boundary = buffer.indexOf('\n\n')
    }

    if (buffer.trim()) {
      processFrame(buffer)
    }

    if (!streamFailed) {
      const finalMessage =
        getSessionMessages(requestSessionId)[assistantIndex]

      if (!receivedContent || !finalMessage?.content.trim()) {
        replaceAssistantMessage(
          requestSessionId,
          assistantIndex,
          '服务已结束，但没有收到可显示的回答正文。请检查后端日志后重试。',
        )
        updateAssistantStatus(
          requestSessionId,
          assistantIndex,
          '未收到回答',
        )
      } else {
        updateAssistantStatus(
          requestSessionId,
          assistantIndex,
          streamFinished ? '回复完成' : '连接已结束',
        )
      }
    }
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error)

    let friendlyMessage =
      '暂时无法连接后端，或流式连接中断。请检查后端是否运行，并稍后重试。'

    if (detail.includes('401')) {
      friendlyMessage = '身份验证失败，请检查 API 认证配置。'
    } else if (detail.includes('400')) {
      friendlyMessage = '请求参数或用户标识无效，请检查前端配置。'
    } else if (detail.includes('HTTP 5')) {
      friendlyMessage = '后端服务发生错误，请检查后端日志后重试。'
    } else if (
      detail.includes('未返回 SSE') ||
      detail.includes('没有返回可读取')
    ) {
      friendlyMessage = detail
    }

    const current = getSessionMessages(requestSessionId)[assistantIndex]

    if (current?.content.trim()) {
      appendAssistantMessage(
        requestSessionId,
        assistantIndex,
        `\n\n> ⚠️ ${friendlyMessage}`,
      )
    } else {
      replaceAssistantMessage(
        requestSessionId,
        assistantIndex,
        friendlyMessage,
      )
    }

    updateAssistantStatus(requestSessionId, assistantIndex, '请求失败')
    console.error('PsyConsult chat request failed:', detail)
  } finally {
    if (reader) {
      try {
        reader.releaseLock()
      } catch {
        // 流读取失败时，释放锁可能再次报错；不覆盖原始错误。
      }
    }

    isThinking.value = false
    await scrollMessages()
  }
}
</script>

<style scoped>
.clinical-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 320px;
  background:
    radial-gradient(circle at top left, oklch(0.94 0.025 195), transparent 34rem),
    linear-gradient(135deg, oklch(0.985 0.006 210), oklch(0.955 0.012 85));
  color: oklch(0.24 0.025 245);
}

.workspace-rail,
.insight-panel {
  min-height: 100vh;
  background: oklch(0.96 0.008 230 / 0.82);
  border-color: oklch(0.84 0.018 235);
  backdrop-filter: blur(10px);
}

.workspace-rail {
  display: flex;
  flex-direction: column;
  gap: 22px;
  padding: 24px 18px;
  border-right: 1px solid oklch(0.84 0.018 235);
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  color: oklch(0.29 0.075 215);
  background: oklch(0.88 0.045 195);
  box-shadow: 0 10px 24px oklch(0.48 0.05 215 / 0.12);
}

.brand-kicker,
.eyebrow,
.section-label {
  color: oklch(0.48 0.035 240);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

.brand-block h1,
.case-header h2,
.empty-copy h3 {
  margin: 0;
  color: oklch(0.2 0.035 245);
  font-weight: 750;
  letter-spacing: 0;
}

.brand-block h1 {
  font-size: 18px;
}

.new-session-button {
  width: 100%;
  min-height: 42px;
  border: 0;
  border-radius: 10px;
  background: oklch(0.43 0.09 225);
  box-shadow: 0 14px 24px oklch(0.38 0.08 225 / 0.2);
}

.session-list {
  display: grid;
  gap: 8px;
  min-height: 0;
  overflow: auto;
}

.session-item {
  width: 100%;
  min-height: 44px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 12px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  color: oklch(0.34 0.028 245);
  cursor: pointer;
  text-align: left;
  transition:
    background-color 180ms ease-out,
    border-color 180ms ease-out,
    color 180ms ease-out;
}

.session-item:hover,
.session-item.active {
  border-color: oklch(0.78 0.035 215);
  background: oklch(0.985 0.006 215);
  color: oklch(0.25 0.07 225);
}

.active-patient-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border: 1px solid oklch(0.78 0.035 190);
  border-radius: 12px;
  background: oklch(0.97 0.025 190);
}
.active-patient-avatar {
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: oklch(0.88 0.045 190);
  color: oklch(0.3 0.07 200);
  font-weight: 750;
}
.active-patient-copy {
  min-width: 0;
}
.active-patient-copy span {
  display: block;
  color: oklch(0.48 0.025 245);
  font-size: 11px;
}
.active-patient-copy strong {
  display: block;
  overflow-wrap: anywhere;
  font-size: 13px;
}
.active-patient-copy button {
  margin-top: 4px;
  padding: 0;
  border: 0;
  background: transparent;
  color: oklch(0.42 0.07 225);
  font-size: 12px;
  cursor: pointer;
}
.doctor-card {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border: 1px solid oklch(0.83 0.018 235);
  border-radius: 12px;
  background: oklch(0.985 0.006 220);
}

.doctor-card span,
.source-item span,
.pipeline-list span {
  display: block;
  color: oklch(0.48 0.025 245);
  font-size: 12px;
}

.doctor-card strong {
  font-size: 14px;
}

.case-workbench {
  min-width: 0;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: 14px;
  padding: 22px;
}

.case-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.case-header h2 {
  font-size: 26px;
}

.service-pill {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  border: 1px solid oklch(0.82 0.02 225);
  border-radius: 999px;
  background: oklch(0.985 0.006 215);
  color: oklch(0.36 0.035 235);
  font-size: 13px;
  font-weight: 700;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: oklch(0.68 0.12 145);
}

.service-pill.active .status-dot {
  background: oklch(0.72 0.14 70);
}

.current-patient-banner {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 10px;
  border: 1px solid oklch(0.78 0.035 190);
  border-radius: 999px;
  background: oklch(0.97 0.025 190);
  color: oklch(0.32 0.065 200);
  font-size: 12px;
  font-weight: 700;
}
.notice-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border: 1px solid oklch(0.84 0.04 80);
  border-radius: 12px;
  background: oklch(0.96 0.035 86);
  color: oklch(0.35 0.05 75);
  font-size: 13px;
}

.messages-panel {
  min-height: 0;
  overflow: auto;
  padding: 22px;
  border: 1px solid oklch(0.84 0.018 235);
  border-radius: 16px;
  background: oklch(0.992 0.004 220 / 0.92);
  box-shadow: 0 20px 60px oklch(0.36 0.04 240 / 0.1);
}

.empty-state {
  display: grid;
  gap: 24px;
}

.empty-copy {
  max-width: 58ch;
}

.empty-copy h3 {
  margin-top: 8px;
  font-size: 28px;
  line-height: 1.15;
}

.empty-copy p:last-child {
  margin-top: 10px;
  color: oklch(0.45 0.028 245);
}

.scenario-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.scenario-card {
  min-height: 128px;
  display: grid;
  grid-template-rows: auto auto 1fr;
  gap: 8px;
  padding: 16px;
  border: 1px solid oklch(0.84 0.02 230);
  border-radius: 12px;
  background: oklch(0.976 0.008 215);
  color: oklch(0.28 0.032 245);
  cursor: pointer;
  text-align: left;
  transition:
    transform 180ms ease-out,
    border-color 180ms ease-out,
    box-shadow 180ms ease-out;
}

.scenario-card:hover {
  transform: translateY(-2px);
  border-color: oklch(0.7 0.05 215);
  box-shadow: 0 16px 28px oklch(0.38 0.05 235 / 0.12);
}

.scenario-icon {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  color: oklch(0.32 0.08 220);
  background: oklch(0.9 0.035 210);
}

.scenario-title {
  font-weight: 750;
}

.scenario-text {
  color: oklch(0.48 0.025 245);
  font-size: 13px;
}

.message-row {
  display: grid;
  gap: 6px;
  margin-bottom: 18px;
}

.message-meta {
  color: oklch(0.52 0.025 245);
  font-size: 12px;
  font-weight: 700;
}

.user-row {
  justify-items: end;
}

.assistant-row {
  justify-items: start;
}

.message-bubble {
  max-width: min(760px, 86%);
  padding: 14px 16px;
  border-radius: 14px;
  line-height: 1.65;
}

.user-bubble {
  color: oklch(0.98 0.006 220);
  background: oklch(0.38 0.08 225);
}

.assistant-bubble {
  border: 1px solid oklch(0.84 0.018 235);
  background: oklch(0.98 0.006 215);
  color: oklch(0.25 0.028 245);
}

.stage-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 100%;
  margin-bottom: 10px;
  padding: 6px 10px;
  border: 1px solid oklch(0.78 0.035 205);
  border-radius: 999px;
  background: oklch(0.95 0.025 205);
  color: oklch(0.34 0.06 220);
  font-size: 13px;
  font-weight: 700;
}

.stage-status span {
  min-width: 0;
  overflow-wrap: anywhere;
}

.markdown-body :deep(p) {
  margin: 0 0 10px;
}

.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 13px;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid oklch(0.82 0.018 235);
  padding: 8px;
  vertical-align: top;
}

.markdown-body :deep(th) {
  background: oklch(0.93 0.012 220);
  font-weight: 750;
}

.thinking-row {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid oklch(0.82 0.02 225);
  border-radius: 999px;
  background: oklch(0.97 0.01 215);
  color: oklch(0.42 0.035 240);
  font-size: 13px;
}

.composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: end;
  padding: 14px;
  border: 1px solid oklch(0.84 0.018 235);
  border-radius: 16px;
  background: oklch(0.985 0.006 215);
  box-shadow: 0 14px 40px oklch(0.36 0.04 240 / 0.08);
}

.save-history-toggle {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 14px;
  color: oklch(0.38 0.055 220);
  font-size: 12px;
}
.save-history-toggle span {
  color: oklch(0.52 0.025 245);
}
.case-input :deep(.el-textarea__inner) {
  min-height: 74px;
  border: 0;
  box-shadow: none;
  background: oklch(0.96 0.008 215);
  color: oklch(0.24 0.025 245);
}

.send-button {
  min-width: 104px;
  min-height: 46px;
  border: 0;
  border-radius: 12px;
  background: oklch(0.43 0.09 225);
}

.insight-panel {
  display: grid;
  align-content: start;
  gap: 18px;
  padding: 24px 18px;
  border-left: 1px solid oklch(0.84 0.018 235);
}

.panel-section {
  display: grid;
  gap: 12px;
}

.pipeline-list {
  display: grid;
  gap: 10px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.pipeline-list li,
.source-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  border: 1px solid oklch(0.84 0.018 235);
  border-radius: 12px;
  background: oklch(0.985 0.006 220);
}

.pipeline-index {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 9px;
  background: oklch(0.9 0.025 215);
  color: oklch(0.32 0.07 225);
  font-size: 12px;
  font-weight: 800;
}

.pipeline-list strong,
.source-item strong {
  display: block;
  color: oklch(0.27 0.03 245);
  font-size: 14px;
}

.source-list {
  display: grid;
  gap: 10px;
}

.source-item > .el-icon {
  margin-top: 2px;
  color: oklch(0.38 0.08 225);
}

@media (max-width: 1180px) {
  .clinical-shell {
    grid-template-columns: 260px minmax(0, 1fr);
  }

  .insight-panel {
    display: none;
  }
}

@media (max-width: 820px) {
  .clinical-shell {
    grid-template-columns: 1fr;
  }

  .workspace-rail {
    min-height: auto;
    border-right: 0;
    border-bottom: 1px solid oklch(0.84 0.018 235);
  }

  .session-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .case-workbench {
    padding: 14px;
  }

  .case-header,
  .composer {
    grid-template-columns: 1fr;
  }

  .case-header {
    align-items: flex-start;
  }

  .scenario-grid {
    grid-template-columns: 1fr;
  }

  .message-bubble {
    max-width: 100%;
  }
}

/* 侧边栏相邻按钮对齐，并覆盖 Element Plus 默认左边距 */
.new-session-button + .new-session-button {
  margin-left: 0 !important;
}
.secondary-nav-button {
  background: oklch(0.96 0.008 215) !important;
  border: 1px solid oklch(0.82 0.02 225) !important;
  color: oklch(0.34 0.035 235) !important;
  box-shadow: none !important;
}


/* Voice recording controls */
.voice-input-row {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  min-width: 0;
}
.voice-record-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 40px;
  padding: 9px 14px;
  border: 1px solid var(--el-border-color, #d8e0e8);
  border-radius: 12px;
  background: var(--el-bg-color, #fff);
  color: var(--el-text-color-primary, #334155);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
  transition: background .15s ease, border-color .15s ease;
}
.voice-record-button:hover:not(:disabled) {
  border-color: var(--el-color-primary, #409eff);
  background: var(--el-fill-color-light, #f5f9ff);
}
.voice-record-button.recording {
  color: #b42318;
  border-color: #f3a6a0;
  background: #fff4f2;
}
.voice-record-button:disabled {
  opacity: .55;
  cursor: not-allowed;
}
.voice-record-icon { font-size: 16px; line-height: 1; }
.voice-note, .voice-status, .voice-error {
  font-size: 12px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.voice-note, .voice-status { color: var(--el-text-color-secondary, #64748b); }
.voice-error { flex-basis: 100%; color: var(--el-color-danger, #c45656); }


.report-file-input {
  display: none;
}

.report-upload-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 36px;
  padding: 7px 12px;
  border: 1px solid oklch(0.82 0.025 225);
  border-radius: 10px;
  background: white;
  color: oklch(0.34 0.055 230);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
}

.report-upload-button:hover:not(:disabled) {
  background: oklch(0.96 0.018 220);
}

.report-upload-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.report-message-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid oklch(0.90 0.012 230);
  color: oklch(0.48 0.025 240);
  font-size: 12px;
}

.report-archive-success {
  margin-top: 10px;
  color: oklch(0.43 0.09 150);
  font-size: 12px;
}

</style>
