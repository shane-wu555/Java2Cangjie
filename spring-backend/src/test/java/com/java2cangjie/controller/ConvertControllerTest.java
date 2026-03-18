package com.java2cangjie.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.java2cangjie.dto.BackendHealthResponse;
import com.java2cangjie.dto.ConvertResponse;
import com.java2cangjie.exception.GlobalExceptionHandler;
import com.java2cangjie.service.ModelGatewayService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(ConvertController.class)
@Import(GlobalExceptionHandler.class)
class ConvertControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private ModelGatewayService modelGatewayService;

    @Test
    void healthShouldReturnDownstreamStatus() throws Exception {
        BackendHealthResponse response = new BackendHealthResponse();
        response.setStatus("ok");
        response.setBackend("ok");
        response.setModelServiceStatus("ok");
        response.setModelLoaded(true);
        response.setModelName("demo-model");
        response.setModelServiceBaseUrl("http://model-service:8001");

        given(modelGatewayService.health()).willReturn(response);

        mockMvc.perform(get("/api/health"))
                .andExpect(status().isOk())
                .andExpect(header().exists("X-Request-Id"))
                .andExpect(jsonPath("$.status").value("ok"))
                .andExpect(jsonPath("$.modelServiceStatus").value("ok"))
                .andExpect(jsonPath("$.modelLoaded").value(true));
    }

    @Test
    void convertShouldReturnValidatedPayload() throws Exception {
        ConvertResponse response = new ConvertResponse();
        response.setCangjieCode("main() {}\n");
        response.setModelName("demo-model");
        response.setQuantization("AWQ-4bit");
        response.setLatencyMs(12);

        given(modelGatewayService.convert(any())).willReturn(response);

        String requestBody = objectMapper.writeValueAsString(new ConvertRequestBody(
                "public class Hello {}",
                512,
                0.1
        ));

        mockMvc.perform(post("/api/convert")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(requestBody))
                .andExpect(status().isOk())
                .andExpect(header().exists("X-Request-Id"))
                .andExpect(jsonPath("$.cangjieCode").value("main() {}\n"))
                .andExpect(jsonPath("$.modelName").value("demo-model"));
    }

    @Test
    void convertShouldRejectBlankJavaCode() throws Exception {
        String requestBody = objectMapper.writeValueAsString(new ConvertRequestBody("", 512, 0.1));

        mockMvc.perform(post("/api/convert")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(requestBody))
                .andExpect(status().isBadRequest())
                .andExpect(header().exists("X-Request-Id"))
                .andExpect(jsonPath("$.message").value("javaCode 不能为空"));
    }

    private record ConvertRequestBody(String javaCode, Integer maxNewTokens, Double temperature) {
    }
}