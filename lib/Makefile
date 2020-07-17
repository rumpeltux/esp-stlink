CFLAGS = -Wall

libespstlink.so: libespstlink.c libespstlink.h
	$(CC) -shared $(CFLAGS) -fPIC $< -o $@

clean:
	rm -f libespstlink.so
