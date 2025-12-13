FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /knowledge ./cmd/main.go

FROM alpine:3.19

COPY --from=builder /knowledge /knowledge

EXPOSE 8003
CMD ["/knowledge"]
