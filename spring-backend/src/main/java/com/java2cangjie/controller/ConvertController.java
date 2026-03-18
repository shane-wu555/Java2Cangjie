package com.java2cangjie.controller;

import com.java2cangjie.dto.BackendHealthResponse;
import com.java2cangjie.dto.ConvertRequest;
import com.java2cangjie.dto.ConvertResponse;
import com.java2cangjie.service.ModelGatewayService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class ConvertController {
    private final ModelGatewayService modelGatewayService;

    public ConvertController(ModelGatewayService modelGatewayService) {
        this.modelGatewayService = modelGatewayService;
    }

    @GetMapping("/health")
    public ResponseEntity<BackendHealthResponse> health() {
        return ResponseEntity.ok(modelGatewayService.health());
    }

    @PostMapping("/convert")
    public ConvertResponse convert(@Valid @RequestBody ConvertRequest request) {
        return modelGatewayService.convert(request);
    }
}
