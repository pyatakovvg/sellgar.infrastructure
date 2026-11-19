{{- define "application.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "application.labels" -}}
{{ include "application.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | quote }}
{{- end }}

{{/* Environment values may be literals or Kubernetes valueFrom references. */}}
{{- define "application.env" -}}
{{- range $name, $value := .Values.env }}
- name: {{ $name | quote }}
  {{- if kindIs "map" $value }}
  {{- toYaml $value | nindent 2 }}
  {{- else }}
  value: {{ $value | quote }}
  {{- end }}
{{- end }}
{{- end }}
