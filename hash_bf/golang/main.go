package main

// please do not use it for bad purposes!

import (
	"crypto/md5"
	"crypto/sha1"
	"crypto/sha256"
	"crypto/sha512"
	"encoding/hex"
	"fmt"
	"strings"
	"time"
)

type HashFunction func([]byte) string

var hashFunctions = map[string]HashFunction{
	"1": func(data []byte) string {
		hash := md5.Sum(data)
		return hex.EncodeToString(hash[:])
	},
	"2": func(data []byte) string {
		hash := sha1.Sum(data)
		return hex.EncodeToString(hash[:])
	},
	"3": func(data []byte) string {
		hash := sha256.Sum256(data)
		return hex.EncodeToString(hash[:])
	},
	"4": func(data []byte) string {
		hash := sha512.Sum512(data)
		return hex.EncodeToString(hash[:])
	},
}

var charsets = map[string]string{
	"1": "0123456789",
	"2": "abcdefghijklmnopqrstuvwxyz",
	"3": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
	"4": " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~",
}

func bruteForce(targetHash string, hashFunc HashFunction, charset string, maxLen int, current string, attempts *int64, found *bool, result *string) {
	if *found || len(current) > maxLen {
		return
	}

	if len(current) > 0 {
		*attempts++
		candidateHash := hashFunc([]byte(current))

		if *attempts%10000 == 0 {
			fmt.Printf("[%d] %s -> %s\n", *attempts, current, candidateHash)
		}

		if candidateHash == targetHash {
			*result = current
			*found = true
			return
		}
	}

	for i := 0; i < len(charset) && !*found; i++ {
		bruteForce(targetHash, hashFunc, charset, maxLen, current+string(charset[i]), attempts, found, result)
	}
}

func main() {
	fmt.Println("=== Hash Brute Force (Go) ===")

	fmt.Println("\nAvailable hash functions:")
	fmt.Println("1) MD5")
	fmt.Println("2) SHA-1")
	fmt.Println("3) SHA-256")
	fmt.Println("4) SHA-512")

	var choice string
	fmt.Print("Choose a hash function (1-4): ")
	fmt.Scanln(&choice)

	hashFunc, exists := hashFunctions[choice]
	if !exists {
		fmt.Println("[!] Invalid choice. Using MD5 by default.")
		hashFunc = hashFunctions["1"]
	}

	var targetHash string
	fmt.Print("\nEnter the hash: ")
	fmt.Scanln(&targetHash)
	targetHash = strings.ToLower(targetHash)

	var maxLen int
	fmt.Print("Maximum password length: ")
	_, err := fmt.Scanln(&maxLen)
	if err != nil || maxLen <= 0 {
		fmt.Println("[!] Invalid input. Using default value (5).")
		maxLen = 5
	}

	if maxLen > 8 {
		fmt.Println("[!] Warning: It will take a very long time to iterate through more than 8 characters!")
	}

	fmt.Println("\nSelect charset:")
	fmt.Println("1) Only numerals (0-9)")
	fmt.Println("2) Only lowercase letters (a-z)")
	fmt.Println("3) All letters and numerals (a-z, A-Z, 0-9)")
	fmt.Println("4) Any printable character")

	var charsetChoice string
	fmt.Print("Your choice (1-4): ")
	fmt.Scanln(&charsetChoice)

	charset, exists := charsets[charsetChoice]
	if !exists {
		fmt.Println("[!] Invalid choice. Using numerals by default.")
		charset = charsets["1"]
	}

	hashName := "MD5"
	switch choice {
	case "2":
		hashName = "SHA-1"
	case "3":
		hashName = "SHA-256"
	case "4":
		hashName = "SHA-512"
	}

	fmt.Printf("\n[+] Using hash function: %s\n", hashName)
	fmt.Printf("[+] Charset: %d symbols\n", len(charset))
	fmt.Printf("[+] Maximum length: %d\n", maxLen)
	fmt.Printf("[+] Total combinations: ")

	totalCombinations := 0
	for i := 1; i <= maxLen; i++ {
		totalCombinations += pow(len(charset), i)
	}
	fmt.Printf("%d\n", totalCombinations)

	fmt.Println("\n" + strings.Repeat("=", 50))

	startTime := time.Now()
	var attempts int64 = 0
	found := false
	var result string

	fmt.Println("[+] Starting brute force...")

	bruteForce(targetHash, hashFunc, charset, maxLen, "", &attempts, &found, &result)

	elapsedTime := time.Since(startTime)

	fmt.Println("\n" + strings.Repeat("=", 50))
	if found {
		fmt.Printf("[+] SUCCESS! Password found: '%s'\n", result)
	} else {
		fmt.Println("[-] Password not found.")
	}
	fmt.Printf("[+] Total attempts: %d\n", attempts)
	fmt.Printf("[+] Time elapsed: %v\n", elapsedTime)
	fmt.Printf("[+] Speed: %.0f attempts/second\n", float64(attempts)/elapsedTime.Seconds())
	fmt.Println(strings.Repeat("=", 50))
}

func pow(base, exponent int) int {
	result := 1
	for i := 0; i < exponent; i++ {
		result *= base
	}
	return result
}
