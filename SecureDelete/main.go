package main

import (
	"crypto/rand"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
)

const (
	defaultPasses = 3
	bufferSize    = 1024 * 1024
)

func overwritePattern(f *os.File, size int64, bytesGenerator func([]byte) error) error {
	if _, err := f.Seek(0, io.SeekStart); err != nil {
		return err
	}

	buf := make([]byte, bufferSize)
	var written int64

	for written < size {
		if err := bytesGenerator(buf); err != nil {
			return err
		}

		remaining := size - written
		chunk := int64(len(buf))
		if remaining < chunk {
			chunk = remaining
		}

		n, err := f.Write(buf[:chunk])
		if err != nil {
			return err
		}
		if int64(n) != chunk {
			return errors.New("short write during overwrite")
		}

		written += chunk
	}

	if err := f.Sync(); err != nil {
		return err
	}

	return nil
}

func secureDelete(path string, passes int, zeroLast bool) error {
	info, err := os.Stat(path)
	if err != nil {
		return err
	}
	if !info.Mode().IsRegular() {
		return fmt.Errorf("'%s' is not a regular file", path)
	}

	size := info.Size()
	if size == 0 {
		return os.Remove(path)
	}

	f, err := os.OpenFile(path, os.O_WRONLY, 0)
	if err != nil {
		return err
	}
	defer f.Close()

	for i := 0; i < passes; i++ {
		pass := i + 1

		var gen func([]byte) error

		switch {
		case pass == 1:
			gen = func(b []byte) error {
				for i := range b {
					b[i] = 0xFF
				}
				return nil
			}
		case pass == 2:
			gen = func(b []byte) error {
				for i := range b {
					b[i] = 0x00
				}
				return nil
			}
		default:
			gen = func(b []byte) error {
				_, err := rand.Read(b)
				return err
			}
		}

		if err := overwritePattern(f, size, gen); err != nil {
			return fmt.Errorf("error on overwrite pass %d: %w", pass, err)
		}
	}

	if zeroLast {
		genZero := func(b []byte) error {
			for i := range b {
				b[i] = 0x00
			}
			return nil
		}
		if err := overwritePattern(f, size, genZero); err != nil {
			return fmt.Errorf("error on final zeroing pass: %w", err)
		}
	}

	if err := f.Truncate(0); err != nil {
		return fmt.Errorf("truncate error: %w", err)
	}
	if err := f.Sync(); err != nil {
		return err
	}

	if err := os.Remove(path); err != nil {
		return fmt.Errorf("file removal error: %w", err)
	}

	return nil
}

func usage() {
	fmt.Fprintf(flag.CommandLine.Output(), "SecureDelete — secure file deletion tool with multi-pass overwrite (DoD-style)\n\n")
	fmt.Fprintf(flag.CommandLine.Output(), "Usage:\n")
	fmt.Fprintf(flag.CommandLine.Output(), "  SecureDelete [options] <file>\n\n")
	fmt.Fprintf(flag.CommandLine.Output(), "Options:\n")
	flag.PrintDefaults()
}

func main() {
	passes := flag.Int("passes", defaultPasses, "number of overwrite passes (default 3)")
	zeroLast := flag.Bool("zero-last", false, "additional final zeroing pass")
	force := flag.Bool("f", false, "do not ask for confirmation")

	flag.Usage = usage
	flag.Parse()

	args := flag.Args()
	if len(args) != 1 {
		usage()
		os.Exit(1)
	}

	path := args[0]

	if *passes <= 0 {
		fmt.Println("Number of passes must be > 0")
		os.Exit(1)
	}

	if !*force {
		fmt.Printf("WARNING: file '%s' will be overwritten %d time(s) and deleted, making recovery extremely difficult.\n", path, *passes)
		if *zeroLast {
			fmt.Println("An additional final zeroing pass will be performed.")
		}
		fmt.Print("Continue? [y/N]: ")

		var answer string
		_, err := fmt.Scanln(&answer)
		if err != nil {
			fmt.Println("Operation cancelled.")
			os.Exit(1)
		}

		if answer != "y" && answer != "Y" && answer != "yes" && answer != "YES" {
			fmt.Println("Operation cancelled by user.")
			os.Exit(0)
		}
	}

	if err := secureDelete(path, *passes, *zeroLast); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("File securely deleted.")
}
