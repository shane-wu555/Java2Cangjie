package com.java2cangjie.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.java2cangjie.dto.BackendHealthResponse;
import com.java2cangjie.dto.ConvertRequest;
import com.java2cangjie.dto.ConvertResponse;
import com.java2cangjie.exception.DownstreamServiceException;
import com.java2cangjie.exception.InvalidDownstreamResponseException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

import java.util.Map;

@Service
public class ModelGatewayService {

    private final RestClient restClient;
    private final String modelServiceBaseUrl;
        private final ObjectMapper objectMapper;

        public ModelGatewayService(
            @Value("${model.service.base-url}") String modelServiceBaseUrl,
            @Value("${model.service.connect-timeout-ms:3000}") int connectTimeoutMs,
            @Value("${model.service.read-timeout-ms:30000}") int readTimeoutMs,
            ObjectMapper objectMapper
        ) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(connectTimeoutMs);
        requestFactory.setReadTimeout(readTimeoutMs);

        this.modelServiceBaseUrl = modelServiceBaseUrl;
        this.objectMapper = objectMapper;
        this.restClient = RestClient.builder()
                .baseUrl(modelServiceBaseUrl)
            .requestFactory(requestFactory)
                .build();
    }

    public BackendHealthResponse health() {
        try {
            Map<?, ?> result = restClient.get()
                    .uri("/health")
                    .retrieve()
                    .body(Map.class);

            if (result == null) {
                throw new InvalidDownstreamResponseException("模型服务健康检查返回为空");
            }

            String modelStatus = readRequiredString(result, "status");
            boolean loaded = readBoolean(result.get("loaded"), "loaded");
            String modelName = readOptionalString(result.get("model"));

            BackendHealthResponse response = new BackendHealthResponse();
            response.setStatus("ok");
            response.setBackend("ok");
            response.setModelServiceStatus(modelStatus);
            response.setModelLoaded(loaded);
            response.setModelName(modelName);
            response.setModelServiceBaseUrl(modelServiceBaseUrl);
            return response;
        } catch (RestClientResponseException ex) {
            throw mapDownstreamException(ex, true);
        } catch (RestClientException ex) {
            throw new DownstreamServiceException(HttpStatus.SERVICE_UNAVAILABLE, "模型服务不可用", ex);
        }
    }

    public ConvertResponse convert(ConvertRequest request) {
        Map<String, Object> payload = Map.of(
                "java_code", request.getJavaCode(),
                "max_new_tokens", request.getMaxNewTokens(),
                "temperature", request.getTemperature()
        );

        try {
            Map<?, ?> result = restClient.post()
                    .uri("/api/v1/convert")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(payload)
                    .retrieve()
                    .body(Map.class);

            if (result == null) {
                throw new InvalidDownstreamResponseException("模型服务返回为空");
            }

            ConvertResponse response = new ConvertResponse();
            response.setCangjieCode(readRequiredString(result, "cangjie_code"));
            response.setModelName(readRequiredString(result, "model_name"));
            response.setQuantization(readRequiredString(result, "quantization"));
            response.setLatencyMs(readInteger(result.get("latency_ms"), "latency_ms"));
            return response;
        } catch (RestClientResponseException ex) {
            throw mapDownstreamException(ex, false);
        } catch (RestClientException ex) {
            throw new DownstreamServiceException(HttpStatus.SERVICE_UNAVAILABLE, "无法连接模型服务", ex);
        }
    }

    private DownstreamServiceException mapDownstreamException(RestClientResponseException ex, boolean healthCheck) {
        String downstreamMessage = extractDownstreamMessage(ex);
        if (ex.getStatusCode().is4xxClientError()) {
            String prefix = healthCheck ? "模型服务健康检查请求被拒绝" : "模型服务拒绝了当前请求";
            return new DownstreamServiceException(HttpStatus.BAD_REQUEST, prefix + "，原因: " + downstreamMessage, ex);
        }

        String prefix = healthCheck ? "模型服务健康检查失败" : "模型服务调用失败";
        return new DownstreamServiceException(HttpStatus.BAD_GATEWAY, prefix + "，原因: " + downstreamMessage, ex);
    }

    private String extractDownstreamMessage(RestClientResponseException ex) {
        String responseBody = ex.getResponseBodyAsString();
        if (responseBody == null || responseBody.isBlank()) {
            return "HTTP 状态码: " + ex.getStatusCode().value();
        }

        try {
            JsonNode root = objectMapper.readTree(responseBody);
            if (root.hasNonNull("message") && !root.get("message").asText().isBlank()) {
                return root.get("message").asText();
            }
            if (root.hasNonNull("detail") && !root.get("detail").asText().isBlank()) {
                return root.get("detail").asText();
            }
            if (root.hasNonNull("error") && !root.get("error").asText().isBlank()) {
                return root.get("error").asText();
            }
        } catch (Exception ignored) {
            // Ignore parse errors and fall back to the raw response body.
        }

        return responseBody;
    }

    private String readRequiredString(Map<?, ?> payload, String key) {
        Object value = payload.get(key);
        if (value instanceof String stringValue && !stringValue.isBlank()) {
            return stringValue;
        }
        throw new InvalidDownstreamResponseException("模型服务返回缺少有效字段: " + key);
    }

    private String readOptionalString(Object value) {
        return value instanceof String stringValue ? stringValue : null;
    }

    private Integer readInteger(Object value, String key) {
        if (value instanceof Number numberValue) {
            return numberValue.intValue();
        }
        throw new InvalidDownstreamResponseException("模型服务返回字段类型错误: " + key);
    }

    private boolean readBoolean(Object value, String key) {
        if (value instanceof Boolean booleanValue) {
            return booleanValue;
        }
        throw new InvalidDownstreamResponseException("模型服务返回字段类型错误: " + key);
    }
}
