package com.java2cangjie.service;

import com.java2cangjie.dto.ConvertRequest;
import com.java2cangjie.dto.ConvertResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.util.Map;

@Service
public class ModelGatewayService {

    private final RestClient restClient;

    public ModelGatewayService(@Value("${model.service.base-url}") String modelServiceBaseUrl) {
        this.restClient = RestClient.builder()
                .baseUrl(modelServiceBaseUrl)
                .build();
    }

    public ConvertResponse convert(ConvertRequest request) {
        Map<String, Object> payload = Map.of(
                "java_code", request.getJavaCode(),
                "max_new_tokens", request.getMaxNewTokens(),
                "temperature", request.getTemperature()
        );

        Map<?, ?> result = restClient.post()
                .uri("/api/v1/convert")
                .contentType(MediaType.APPLICATION_JSON)
                .body(payload)
                .retrieve()
                .body(Map.class);

        ConvertResponse response = new ConvertResponse();
        response.setCangjieCode((String) result.get("cangjie_code"));
        response.setModelName((String) result.get("model_name"));
        response.setQuantization((String) result.get("quantization"));
        response.setLatencyMs((Integer) result.get("latency_ms"));
        return response;
    }
}
