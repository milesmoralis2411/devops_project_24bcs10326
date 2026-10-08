{{/* Chart name, overridable. */}}
{{- define "stockpilot.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Fully qualified app name. If the release is already called "stockpilot" we do not
repeat it, so `helm install stockpilot` gives stockpilot-backend, stockpilot-frontend...
*/}}
{{- define "stockpilot.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "stockpilot.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* Labels shared by every object. */}}
{{- define "stockpilot.labels" -}}
helm.sh/chart: {{ include "stockpilot.chart" . }}
app.kubernetes.io/name: {{ include "stockpilot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: stockpilot
{{- end }}

{{/*
Selector labels for one component. Usage:
  include "stockpilot.selectorLabels" (dict "ctx" . "component" "backend")
A Service only sends traffic to Pods whose labels match its selector exactly.
*/}}
{{- define "stockpilot.selectorLabels" -}}
app.kubernetes.io/name: {{ include "stockpilot.name" .ctx }}
app.kubernetes.io/instance: {{ .ctx.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{- define "stockpilot.componentLabels" -}}
{{ include "stockpilot.labels" .ctx }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{- define "stockpilot.backendName" -}}{{ include "stockpilot.fullname" . }}-backend{{- end }}
{{- define "stockpilot.frontendName" -}}{{ include "stockpilot.fullname" . }}-frontend{{- end }}
{{- define "stockpilot.postgresName" -}}{{ include "stockpilot.fullname" . }}-postgres{{- end }}
{{- define "stockpilot.dbSecretName" -}}{{ include "stockpilot.fullname" . }}-db{{- end }}

{{/* Image reference; the tag defaults to the chart appVersion when CI did not set one. */}}
{{- define "stockpilot.image" -}}
{{- printf "%s:%s" .image.repository (default .ctx.Chart.AppVersion .image.tag | toString) }}
{{- end }}

{{/* Pod-level security context satisfying the "restricted" Pod Security Standard. */}}
{{- define "stockpilot.podSecurityContext" -}}
runAsNonRoot: true
runAsUser: {{ .uid }}
runAsGroup: {{ .uid }}
fsGroup: {{ .uid }}
seccompProfile:
  type: RuntimeDefault
{{- end }}

{{- define "stockpilot.containerSecurityContext" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities:
  drop: ["ALL"]
{{- end }}
