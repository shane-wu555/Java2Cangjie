package com.java2cangjie.dto;

public class BackendHealthResponse {
    private String status;
    private String backend;
    private String modelServiceStatus;
    private boolean modelLoaded;
    private String modelName;
    private String modelServiceBaseUrl;

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getBackend() {
        return backend;
    }

    public void setBackend(String backend) {
        this.backend = backend;
    }

    public String getModelServiceStatus() {
        return modelServiceStatus;
    }

    public void setModelServiceStatus(String modelServiceStatus) {
        this.modelServiceStatus = modelServiceStatus;
    }

    public boolean isModelLoaded() {
        return modelLoaded;
    }

    public void setModelLoaded(boolean modelLoaded) {
        this.modelLoaded = modelLoaded;
    }

    public String getModelName() {
        return modelName;
    }

    public void setModelName(String modelName) {
        this.modelName = modelName;
    }

    public String getModelServiceBaseUrl() {
        return modelServiceBaseUrl;
    }

    public void setModelServiceBaseUrl(String modelServiceBaseUrl) {
        this.modelServiceBaseUrl = modelServiceBaseUrl;
    }
}