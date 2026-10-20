<template>
  <section class="assessment-view">
    <div class="intro-card">
      <div>
        <span class="eyebrow">SELF-ASSESSMENT</span>
        <h3>了解近期的情绪与心理状态</h3>
        <p>
          请根据过去两周的实际情况逐项作答。系统将依据你提交的答案计算分数，
          不会让大模型推测或补全未回答的题目。
        </p>
      </div>
    </div>

    <div class="prototype-notice">
      <strong>原型验证说明</strong>
      <p>
        当前中文题项用于功能演示，正式使用前须核对经验证的中文版量表。
        结果仅用于筛查，不构成诊断。
      </p>
    </div>

    <div class="scale-selector" role="group" aria-label="选择自评量表">
      <button
        v-for="scale in scaleOptions"
        :key="scale.value"
        type="button"
        class="scale-tab"
        :class="{ selected: scaleType === scale.value }"
        :aria-pressed="scaleType === scale.value"
        @click="selectScale(scale.value)"
      >
        <strong>{{ scale.label }}</strong>
        <span>{{ scale.description }}</span>
      </button>
    </div>

    <div class="question-heading">
      <div>
        <h3>{{ scaleType }} 自评问卷</h3>
        <p>以下问题在过去两周内困扰你的频率如何？</p>
      </div>
      <span class="progress-label">
        已完成 {{ answeredCount }} / {{ questionSet.length }} 题
      </span>
    </div>

    <div class="progress-track" aria-hidden="true">
      <div class="progress-fill" :style="{ width: `${progress}%` }"></div>
    </div>

    <form class="question-list" @submit.prevent="submitAssessment">
      <fieldset
        v-for="(question, index) in questionSet"
        :key="`${scaleType}-${index}`"
        class="question-card"
      >
        <legend class="question-title">
          <span class="question-number">{{ String(index + 1).padStart(2, '0') }}</span>
          <span>{{ question }}</span>
        </legend>

        <div class="option-grid">
          <button
            v-for="option in frequencyOptions"
            :key="option.value"
            type="button"
            class="option-button"
            :class="{ selected: answers[index] === option.value }"
            :aria-pressed="answers[index] === option.value"
            @click="setAnswer(index, option.value)"
          >
            <span class="option-score">{{ option.value }}</span>
            <span>{{ option.label }}</span>
          </button>
        </div>
      </fieldset>

      <p v-if="errorMessage" class="error-message" role="alert">
        {{ errorMessage }}
      </p>

      <div class="submit-row">
        <span class="completion-hint">
          {{ isComplete ? '所有题目均已作答，可以提交。' : '请完成全部题目后再提交。' }}
        </span>
        <label v-if="patientId" class="save-record-option">
          <input v-model="saveToRecord" type="checkbox">
          将本次结果保存到当前患者档案
        </label>
        <button
          type="submit"
          class="submit-button"
          :disabled="!isComplete || isSubmitting"
        >
          {{ isSubmitting ? '正在计算…' : '提交并计算结果' }}
        </button>
      </div>
    </form>

    <section v-if="result" class="result-card" aria-live="polite">
      <span class="eyebrow">ASSESSMENT RESULT</span>
      <h3>筛查结果</h3>
      <p v-if="result.answers_stored" class="saved-record-note">本次结果已保存到当前患者档案。</p>

      <div class="result-summary">
        <div class="result-score">
          <strong>{{ result.total }}</strong>
          <span>/ {{ maxScore }} 分</span>
        </div>
        <div class="result-band">
          <span>当前分数对应的症状程度分层</span>
          <strong>{{ result.severity_band }}</strong>
        </div>
      </div>

      <p class="result-note">{{ result.interpretation_note }}</p>

      <div v-if="result.safety_alert" class="safety-alert" role="alert">
        <strong>请关注当前安全状况</strong>
        <p>{{ result.safety_alert }}</p>
      </div>
    </section>

    <p class="privacy-note">
      未勾选保存时，答案仅用于本次计分，不会写入档案；勾选后会将答案和结果保存到当前患者记录。
      本原型请使用虚拟患者数据，不要录入真实身份信息。
    </p>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

type ScaleType = 'PHQ-9' | 'GAD-7'

interface AssessmentResult {
  status: 'success'
  scale_type: ScaleType
  item_count: number
  total: number
  severity_band: string
  screening_only: boolean
  calculation_method: string
  answers_stored: boolean
  interpretation_note: string
  safety_alert: string | null
  record_id?: string
  created_at?: string
}

const props = defineProps<{
  apiBaseUrl: string
  apiAuthToken: string
  userId: string
  patientId: string | null
}>()

const scaleOptions: Array<{
  value: ScaleType
  label: string
  description: string
}> = [
  { value: 'PHQ-9', label: 'PHQ-9', description: '抑郁症状自评 · 9 题' },
  { value: 'GAD-7', label: 'GAD-7', description: '焦虑症状自评 · 7 题' },
]

const frequencyOptions = [
  { value: 0, label: '完全没有' },
  { value: 1, label: '有几天' },
  { value: 2, label: '一半以上的天数' },
  { value: 3, label: '几乎每天' },
]

const phq9Questions = [
  '做事时提不起劲或没有兴趣。',
  '感到心情低落、沮丧或绝望。',
  '入睡困难、睡不安稳，或睡得过多。',
  '感到疲倦或没有活力。',
  '胃口不好或吃得太多。',
  '觉得自己很糟糕，或觉得自己是失败者，或让自己或家人失望。',
  '做事时难以集中注意力，例如阅读或看电视。',
  '动作或说话缓慢到别人能察觉，或相反，烦躁或坐立不安、活动比平时多。',
  '有不如死掉或以某种方式伤害自己的念头。',
]

const gad7Questions = [
  '感到紧张、焦虑或急切。',
  '无法停止或控制担忧。',
  '对各种事情担忧过多。',
  '很难放松下来。',
  '因为不安而难以静坐。',
  '变得容易烦恼或急躁。',
  '感到似乎将有可怕的事情发生。',
]

const scaleType = ref<ScaleType>('PHQ-9')
const answers = ref<Array<number | null>>(Array(9).fill(null))
const result = ref<AssessmentResult | null>(null)
const errorMessage = ref('')
const isSubmitting = ref(false)
const saveToRecord = ref(false)

const questionSet = computed(() =>
  scaleType.value === 'PHQ-9' ? phq9Questions : gad7Questions,
)

const answeredCount = computed(() =>
  answers.value.filter((answer) => answer !== null).length,
)

const isComplete = computed(() =>
  answers.value.length === questionSet.value.length &&
  answers.value.every((answer) => answer !== null),
)

const progress = computed(() =>
  questionSet.value.length
    ? (answeredCount.value / questionSet.value.length) * 100
    : 0,
)

const maxScore = computed(() => questionSet.value.length * 3)

watch(scaleType, () => {
  answers.value = Array(questionSet.value.length).fill(null)
  result.value = null
  errorMessage.value = ''
})

watch(() => props.patientId, () => {
  // Prevent a result intended for one patient from being silently saved to another.
  saveToRecord.value = false
  result.value = null
  errorMessage.value = ''
})

function selectScale(value: ScaleType) {
  if (scaleType.value !== value) {
    scaleType.value = value
  }
}

function setAnswer(index: number, value: number) {
  answers.value[index] = value
  result.value = null
  errorMessage.value = ''
}

async function submitAssessment() {
  if (!isComplete.value || isSubmitting.value) return

  isSubmitting.value = true
  errorMessage.value = ''
  result.value = null

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-User-Id': props.userId,
  }

  if (props.apiAuthToken) {
    headers.Authorization = `Bearer ${props.apiAuthToken}`
  }

  try {
    const patientIdAtSubmit = props.patientId
    const endpoint = saveToRecord.value && patientIdAtSubmit
      ? `${props.apiBaseUrl}/api/patients/${patientIdAtSubmit}/assessments`
      : `${props.apiBaseUrl}/api/assessment/score`

    const response = await fetch(endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        scale_type: scaleType.value,
        answers: answers.value as number[],
      }),
    })

    const body = await response.json().catch(() => null)

    if (!response.ok) {
      const detail = body?.detail
      throw new Error(
        typeof detail === 'string'
          ? detail
          : `评分请求失败（HTTP ${response.status}），请检查后端服务及认证配置。`,
      )
    }

    result.value = body as AssessmentResult
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : '请求失败，请检查后端服务和网络连接。'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.assessment-view {
  box-sizing: border-box;
  width: 100%;
  max-width: 1040px;
  margin: 0 auto;
  padding: 22px 24px 32px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  color: #243247;
}

.intro-card,
.question-card,
.result-card {
  border: 1px solid #e1e8f0;
  border-radius: 14px;
  background: #fff;
}

.intro-card {
  padding: 22px 24px;
  background: linear-gradient(135deg, #f2f7ff, #ffffff 76%);
}

.eyebrow {
  display: block;
  margin-bottom: 8px;
  color: #5378a8;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.intro-card h3,
.result-card h3 {
  margin: 0 0 10px;
  font-size: 21px;
  line-height: 1.45;
}

.intro-card p,
.question-heading p,
.result-note,
.privacy-note {
  margin: 0;
  color: #65748a;
  font-size: 13px;
  line-height: 1.8;
}

.prototype-notice {
  padding: 13px 16px;
  border: 1px solid #f1d9a8;
  border-radius: 10px;
  background: #fffaf0;
  color: #79541b;
  font-size: 12px;
  line-height: 1.7;
}

.prototype-notice p {
  margin: 3px 0 0;
}

.scale-selector {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.scale-tab {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  padding: 16px 18px;
  border: 1px solid #dce4ee;
  border-radius: 12px;
  background: #fff;
  color: #34445a;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.scale-tab strong {
  font-size: 16px;
}

.scale-tab span {
  color: #728096;
  font-size: 12px;
}

.scale-tab.selected {
  border-color: #5482c2;
  background: #f1f6ff;
  box-shadow: inset 0 0 0 1px #5482c2;
}

.question-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.question-heading h3 {
  margin: 0 0 5px;
  font-size: 18px;
}

.progress-label {
  flex-shrink: 0;
  color: #5378a8;
  font-size: 12px;
}

.progress-track {
  height: 5px;
  overflow: hidden;
  border-radius: 999px;
  background: #e8edf4;
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: #5482c2;
  transition: width 0.2s;
}

.question-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.question-card {
  min-width: 0;
  margin: 0;
  padding: 17px 18px 18px;
}

.question-title {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  width: 100%;
  margin-bottom: 16px;
  padding: 0;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.7;
}

.question-number {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: #edf3fc;
  color: #426b9f;
  font-size: 11px;
}

.option-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 9px;
}

.option-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 78px;
  padding: 10px 6px;
  border: 1px solid #dfe6ee;
  border-radius: 10px;
  background: #fff;
  color: #536176;
  font-size: 12px;
  line-height: 1.5;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.option-button:hover {
  border-color: #8ca9d0;
}

.option-score {
  font-size: 17px;
  font-weight: 700;
}

.option-button.selected {
  border-color: #5482c2;
  background: #edf4ff;
  color: #315d95;
  box-shadow: inset 0 0 0 1px #5482c2;
}

.submit-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding-top: 4px;
}

.completion-hint {
  color: #728096;
  font-size: 12px;
}

.submit-button {
  padding: 12px 22px;
  border: 0;
  border-radius: 9px;
  background: #416fae;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.submit-button:disabled {
  background: #b7c4d5;
  cursor: not-allowed;
}

.error-message {
  margin: 0;
  color: #b42318;
  font-size: 13px;
  line-height: 1.7;
}

.result-card {
  padding: 22px 24px;
}

.result-summary {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 28px;
  margin: 18px 0;
}

.result-score {
  display: flex;
  align-items: baseline;
  gap: 7px;
}

.result-score strong {
  color: #315d95;
  font-size: 42px;
  line-height: 1.1;
}

.result-score span,
.result-band span {
  color: #728096;
  font-size: 12px;
}

.result-band {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.result-band strong {
  color: #315d95;
  font-size: 17px;
}

.result-note {
  padding-top: 14px;
  border-top: 1px solid #e8edf4;
}

.safety-alert {
  margin-top: 16px;
  padding: 16px;
  border: 1px solid #efb7b3;
  border-radius: 10px;
  background: #fff3f2;
  color: #922b24;
  line-height: 1.8;
}

.safety-alert p {
  margin: 5px 0 0;
  font-size: 13px;
}

.save-record-option {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #315d95;
  font-size: 12px;
}
.save-record-option input {
  accent-color: #416fae;
}
.saved-record-note {
  margin: 8px 0 0;
  color: #13805d;
  font-size: 13px;
  font-weight: 600;
}
.privacy-note {
  font-size: 11px;
}

@media (max-width: 760px) {
  .assessment-view {
    padding: 16px 12px 24px;
  }

  .scale-selector {
    grid-template-columns: 1fr;
  }

  .option-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .question-heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .submit-row {
    align-items: stretch;
    flex-direction: column;
  }

  .submit-button {
    width: 100%;
  }
}
</style>
