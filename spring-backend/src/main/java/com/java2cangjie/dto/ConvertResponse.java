package com.java2cangjie.dto;

public class ConvertResponse {
    private String cangjieCode;
    private String modelName;
    private String quantization;
    private Integer latencyMs;

    public String getCangjieCode() {
        return cangjieCode;
    }

    public void setCangjieCode(String cangjieCode) {
        this.cangjieCode = cangjieCode;
    }

    public String getModelName() {
        return modelName;
    }

    public void setModelName(String modelName) {
        this.modelName = modelName;
    }

    public String getQuantization() {
        return quantization;
    }

    public void setQuantization(String quantization) {
        this.quantization = quantization;
    }

    public Integer getLatencyMs() {
        return latencyMs;
    }

    public void setLatencyMs(Integer latencyMs) {
        this.latencyMs = latencyMs;
    }
}
