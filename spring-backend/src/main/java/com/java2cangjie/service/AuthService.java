package com.java2cangjie.service;

import com.java2cangjie.dto.AuthRequest;
import com.java2cangjie.dto.AuthResponse;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.HexFormat;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class AuthService {

    // 内存存储：username -> "salt:hashedPassword"
    private final Map<String, String> users = new ConcurrentHashMap<>();
    // 内存存储：token -> username
    private final Map<String, String> tokens = new ConcurrentHashMap<>();

    private static final SecureRandom RANDOM = new SecureRandom();

    public AuthResponse register(AuthRequest request) {
        String username = request.getUsername().trim();
        if (users.containsKey(username)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "用户名已被占用，请换一个用户名。");
        }
        String salt = generateSalt();
        String hashed = hash(request.getPassword(), salt);
        users.put(username, salt + ":" + hashed);

        String token = UUID.randomUUID().toString();
        tokens.put(token, username);
        return new AuthResponse(token, username);
    }

    public AuthResponse login(AuthRequest request) {
        String username = request.getUsername().trim();
        String stored = users.get(username);
        if (stored == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "用户名或密码错误。");
        }
        String[] parts = stored.split(":", 2);
        String salt = parts[0];
        String expected = parts[1];
        if (!expected.equals(hash(request.getPassword(), salt))) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "用户名或密码错误。");
        }
        String token = UUID.randomUUID().toString();
        tokens.put(token, username);
        return new AuthResponse(token, username);
    }

    public String getUsernameByToken(String token) {
        return tokens.get(token);
    }

    private String generateSalt() {
        byte[] bytes = new byte[16];
        RANDOM.nextBytes(bytes);
        return Base64.getEncoder().encodeToString(bytes);
    }

    private String hash(String password, String salt) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            md.update((salt + password).getBytes());
            return HexFormat.of().formatHex(md.digest());
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("Hash algorithm unavailable", e);
        }
    }
}
