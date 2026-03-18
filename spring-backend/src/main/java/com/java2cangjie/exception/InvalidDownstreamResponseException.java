package com.java2cangjie.exception;

public class InvalidDownstreamResponseException extends RuntimeException {
    public InvalidDownstreamResponseException(String message) {
        super(message);
    }
}