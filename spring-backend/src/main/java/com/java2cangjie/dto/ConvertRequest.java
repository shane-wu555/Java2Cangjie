package com.java2cangjie.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;

public class ConvertRequest {
    @NotBlank(message = "javaCode 不能为空")
    private String javaCode;

    @Min(16)
    @Max(4096)
    private Integer maxNewTokens = 512;

    @Min(0)
    @Max(2)
    private Double temperature = 0.1;

    public String getJavaCode() {
        return javaCode;
    }

    public void setJavaCode(String javaCode) {
        this.javaCode = javaCode;
    }

    public Integer getMaxNewTokens() {
        return maxNewTokens;
    }

    public void setMaxNewTokens(Integer maxNewTokens) {
        this.maxNewTokens = maxNewTokens;
    }

    public Double getTemperature() {
        return temperature;
    }

    public void setTemperature(Double temperature) {
        this.temperature = temperature;
    }
}
